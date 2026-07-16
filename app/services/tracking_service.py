from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.constants.enums import NotificationDTO, TrackingStatus
from app.models import Carrier, Tracking, TrackingEvent, User
from app.providers import build_provider_registry
from app.providers.base import InvalidTrackingCodeError, TrackingProvider
from app.services.carrier_service import detect_carrier, is_valid_for_carrier
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class TrackingService:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        check_interval_minutes: int = 5,
        provider_registry: dict[str, TrackingProvider] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._check_interval_minutes = check_interval_minutes
        self._provider_registry = provider_registry or build_provider_registry()
        self._user_service = UserService(session_factory)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _insert_event_if_new(session: Session, tracking: Tracking, event) -> None:
        existed = session.scalar(
            select(TrackingEvent.id).where(
                TrackingEvent.tracking_id == tracking.id,
                TrackingEvent.event_hash == event.event_hash,
            )
        )
        if existed is not None:
            return
        session.add(
            TrackingEvent(
                tracking_id=tracking.id,
                status=event.status.value,
                description=event.description,
                location=event.location,
                event_time=event.event_time,
                event_hash=event.event_hash,
            )
        )

    def _sync_tracking_history(
        self,
        session: Session,
        tracking: Tracking,
        provider: TrackingProvider,
        *,
        require_history: bool = False,
        notify: bool = True,
    ) -> list[NotificationDTO]:
        new_events: list[NotificationDTO] = []

        history = provider.fetch_event_history(tracking.tracking_code)
        if not history:
            if require_history:
                raise InvalidTrackingCodeError(f"No history for: {tracking.tracking_code}")
            latest = provider.fetch_latest_event(
                tracking_code=tracking.tracking_code,
                current_status=(
                    TrackingStatus(tracking.last_status) if tracking.last_status else None
                ),
            )
            history = [latest]

        if not history:
            return new_events

        existing_hashes = {
            row[0]
            for row in session.execute(
                select(TrackingEvent.event_hash).where(
                    TrackingEvent.tracking_id == tracking.id
                )
            ).all()
        }
        last_known_hash = tracking.last_event_hash
        found_last_known = False

        for event in history:
            is_new = event.event_hash not in existing_hashes
            self._insert_event_if_new(session, tracking, event)
            existing_hashes.add(event.event_hash)

            if last_known_hash and event.event_hash == last_known_hash:
                found_last_known = True
                continue

            if notify and is_new and (last_known_hash is None or found_last_known):
                new_events.append(
                    NotificationDTO(
                        tracking_code=tracking.tracking_code,
                        carrier_code=tracking.carrier.code,
                        status=event.status,
                        description=event.description,
                        location=event.location,
                        event_time=event.event_time,
                    )
                )

        latest_event = history[-1]
        tracking.last_status = latest_event.status.value
        tracking.last_event_hash = latest_event.event_hash
        if latest_event.status == TrackingStatus.DELIVERED:
            tracking.is_active = False
            tracking.next_check_at = None
            logger.info(
                "Tracking completed and monitoring stopped: code=%s",
                tracking.tracking_code,
            )
        return new_events

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_tracking(
        self,
        telegram_chat_id: int,
        tracking_code: str,
        carrier_code_override: str | None = None,
    ) -> Tracking:
        normalized_code = tracking_code.strip().upper()
        if not normalized_code:
            raise ValueError("error.empty_tracking_code")

        carrier_code = (
            carrier_code_override.lower()
            if carrier_code_override
            else detect_carrier(normalized_code)
        )
        if carrier_code is None:
            raise ValueError("error.unsupported_tracking_code")
        if not is_valid_for_carrier(normalized_code, carrier_code):
            raise ValueError("error.invalid_tracking_code")

        with self._session_factory() as session:
            user = self._user_service.get_or_create_user(session, telegram_chat_id)
            carrier = session.scalar(select(Carrier).where(Carrier.code == carrier_code))
            if carrier is None:
                raise ValueError(f"error.carrier_not_configured:{carrier_code}")

            provider = self._provider_registry.get(carrier_code)

            existing = session.scalar(
                select(Tracking).where(
                    Tracking.user_id == user.id,
                    Tracking.carrier_id == carrier.id,
                    Tracking.tracking_code == normalized_code,
                )
            )

            now = datetime.now(timezone.utc)
            if existing:
                is_completed = existing.last_status == TrackingStatus.DELIVERED.value
                existing.is_active = not is_completed
                existing.is_deleted = False
                existing.next_check_at = None if is_completed else now
                tracking = existing
            else:
                if user.credits <= 0:
                    raise ValueError("error.insufficient_credits")
                user.credits -= 1
                tracking = Tracking(
                    user_id=user.id,
                    carrier_id=carrier.id,
                    tracking_code=normalized_code,
                    last_status=TrackingStatus.CREATED.value,
                    last_event_hash=None,
                    next_check_at=now,
                    is_active=True,
                )
                session.add(tracking)

            session.flush()

            if provider is not None and tracking.last_status != TrackingStatus.DELIVERED.value:
                try:
                    require_history = existing is None and carrier_code == "shopeeexpress"
                    self._sync_tracking_history(
                        session, tracking, provider,
                        require_history=require_history,
                        notify=False,
                    )
                except InvalidTrackingCodeError as e:
                    logger.warning("Invalid tracking code '%s': %s", normalized_code, str(e))
                    raise ValueError("error.invalid_tracking_code")
                except ValueError as e:
                    logger.warning("Failed to fetch tracking '%s': %s", normalized_code, str(e))
                    raise ValueError("error.tracking_fetch_failed")
                except Exception:
                    logger.exception("Initial sync failed for '%s'", normalized_code)
                    raise ValueError("error.tracking_fetch_failed")

            session.commit()
            session.refresh(tracking)
            session.refresh(carrier)
            tracking.carrier = carrier
            logger.info(
                "Tracking added: user=%s code=%s carrier=%s",
                telegram_chat_id, normalized_code, carrier_code,
            )
            return tracking

    def list_trackings(self, telegram_chat_id: int) -> list[Tracking]:
        with self._session_factory() as session:
            user = session.scalar(
                select(User).where(User.telegram_chat_id == telegram_chat_id)
            )
            if user is None:
                return []
            return list(
                session.scalars(
                    select(Tracking)
                    .options(joinedload(Tracking.carrier))
                    .where(
                        Tracking.user_id == user.id,
                        Tracking.is_deleted.is_(False),
                    )
                    .order_by(Tracking.created_at.desc())
                ).all()
            )

    def get_tracking_detail(
        self, telegram_chat_id: int, tracking_id: int
    ) -> Tracking | None:
        with self._session_factory() as session:
            user = session.scalar(
                select(User).where(User.telegram_chat_id == telegram_chat_id)
            )
            if user is None:
                return None
            return session.scalar(
                select(Tracking)
                .options(joinedload(Tracking.carrier))
                .where(Tracking.id == tracking_id, Tracking.user_id == user.id)
            )

    def toggle_tracking_notification(
        self, telegram_chat_id: int, tracking_id: int
    ) -> bool | None:
        """Toggle notifications; verifies ownership before changing."""
        with self._session_factory() as session:
            tracking = session.scalar(
                select(Tracking)
                .join(User, Tracking.user_id == User.id)
                .where(
                    Tracking.id == tracking_id,
                    User.telegram_chat_id == telegram_chat_id,
                )
            )
            if tracking is None:
                return None
            tracking.notification_enabled = not tracking.notification_enabled
            session.commit()
            return tracking.notification_enabled

    def get_tracking_events(
        self, telegram_chat_id: int, tracking_id: int
    ) -> list[TrackingEvent]:
        with self._session_factory() as session:
            user = session.scalar(
                select(User).where(User.telegram_chat_id == telegram_chat_id)
            )
            if user is None:
                return []
            tracking = session.scalar(
                select(Tracking).where(
                    Tracking.id == tracking_id, Tracking.user_id == user.id
                )
            )
            if tracking is None:
                return []
            return list(
                session.scalars(
                    select(TrackingEvent)
                    .where(TrackingEvent.tracking_id == tracking_id)
                    .order_by(TrackingEvent.event_time.asc())
                ).all()
            )

    def remove_tracking(self, telegram_chat_id: int, tracking_code: str) -> bool:
        normalized_code = tracking_code.strip().upper()
        with self._session_factory() as session:
            user = session.scalar(
                select(User).where(User.telegram_chat_id == telegram_chat_id)
            )
            if user is None:
                return False
            tracking = session.scalar(
                select(Tracking).where(
                    Tracking.user_id == user.id,
                    Tracking.tracking_code == normalized_code,
                )
            )
            if tracking is None:
                return False
            tracking.is_active = False
            tracking.is_deleted = True
            tracking.next_check_at = None
            session.commit()
            logger.info(
                "Tracking removed: user=%s code=%s", telegram_chat_id, normalized_code
            )
            return True
