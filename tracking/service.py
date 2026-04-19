from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from db.models import Carrier, Tracking, TrackingEvent, User
from tracking.providers import build_provider_registry
from tracking.providers.base import InvalidTrackingCodeError, TrackingProvider
from tracking.types import NotificationDTO, TrackingStatus

logger = logging.getLogger(__name__)

SUPPORTED_CARRIERS = {
    "jtexpress": "JT Express",
    "shopeeexpress": "Shopee Express",
}


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

    @staticmethod
    def detect_carrier(tracking_code: str) -> str | None:
        code = tracking_code.strip().upper()

        if code.startswith("SPX") or code.startswith("SLS"):
            return "shopeeexpress"

        if code.startswith("JT"):
            return "jtexpress"

        if code.isdigit() and 10 <= len(code) <= 15:
            return "jtexpress"

        return None

    @staticmethod
    def _is_valid_for_carrier(tracking_code: str, carrier_code: str) -> bool:
        code = tracking_code.strip().upper()
        carrier = carrier_code.strip().lower()

        if carrier == "shopeeexpress":
            return code.startswith("SPX") or code.startswith("SLS")

        if carrier == "jtexpress":
            return code.startswith("JT") or (code.isdigit() and 10 <= len(code) <= 15)

        return True

    def seed_carriers(self) -> None:
        with self._session_factory() as session:
            existing = {
                row[0]
                for row in session.execute(select(Carrier.code)).all()
            }
            for code, name in SUPPORTED_CARRIERS.items():
                if code not in existing:
                    session.add(Carrier(code=code, name=name))
            session.commit()
            logger.info("Carriers seeded: %s", list(SUPPORTED_CARRIERS.keys()))

    def _get_or_create_user(self, session: Session, telegram_chat_id: int) -> User:
        user = session.scalar(select(User).where(User.telegram_chat_id == telegram_chat_id))
        if user is None:
            user = User(telegram_chat_id=telegram_chat_id)
            session.add(user)
            session.flush()
        return user

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
        """Sync tracking history and return list of NEW events (not seen before)."""
        new_events: list[NotificationDTO] = []

        history = provider.fetch_event_history(tracking.tracking_code)
        if not history:
            if require_history:
                raise InvalidTrackingCodeError(f"No provider history for tracking code: {tracking.tracking_code}")
            latest = provider.fetch_latest_event(
                tracking_code=tracking.tracking_code,
                current_status=TrackingStatus(tracking.last_status) if tracking.last_status else None,
            )
            history = [latest]

        if not history:
            return new_events

        existing_hashes = {
            row[0]
            for row in session.execute(
                select(TrackingEvent.event_hash).where(TrackingEvent.tracking_id == tracking.id)
            ).all()
        }

        last_known_hash = tracking.last_event_hash

        for event in history:
            is_new = event.event_hash not in existing_hashes
            self._insert_event_if_new(session, tracking, event)
            existing_hashes.add(event.event_hash)

            # Only notify for events that appeared AFTER the last known state
            if notify and is_new and last_known_hash is not None:
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

        return new_events

    def add_tracking(self, telegram_chat_id: int, tracking_code: str, carrier_code_override: str | None = None) -> Tracking:
        normalized_code = tracking_code.strip().upper()
        if not normalized_code:
            raise ValueError("error.empty_tracking_code")

        if carrier_code_override:
            carrier_code = carrier_code_override.lower()
        else:
            carrier_code = self.detect_carrier(normalized_code)
            if carrier_code is None:
                raise ValueError("error.unsupported_tracking_code")

        if not self._is_valid_for_carrier(normalized_code, carrier_code):
            raise ValueError("error.invalid_tracking_code")

        with self._session_factory() as session:
            user = self._get_or_create_user(session, telegram_chat_id)
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
                existing.is_active = True
                existing.next_check_at = now
                tracking = existing
            else:
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

            if provider is not None:
                try:
                    require_history = existing is None and carrier_code == "shopeeexpress"
                    self._sync_tracking_history(session, tracking, provider, require_history=require_history, notify=False)
                except InvalidTrackingCodeError:
                    raise ValueError("error.invalid_tracking_code")
                except Exception:
                    logger.exception("Initial provider history sync failed for tracking '%s'", normalized_code)

            session.commit()
            session.refresh(tracking)
            session.refresh(carrier)
            tracking.carrier = carrier
            logger.info("Tracking added: user=%s code=%s carrier=%s", telegram_chat_id, normalized_code, carrier_code)
            return tracking

    def list_trackings(self, telegram_chat_id: int) -> list[Tracking]:
        with self._session_factory() as session:
            user = session.scalar(select(User).where(User.telegram_chat_id == telegram_chat_id))
            if user is None:
                return []

            rows = session.scalars(
                select(Tracking)
                .options(joinedload(Tracking.carrier))
                .where(Tracking.user_id == user.id, Tracking.is_active.is_(True))
                .order_by(Tracking.next_check_at.asc())
            ).all()
            return list(rows)

    def get_user_profile_summary(self, telegram_chat_id: int) -> dict[str, object]:
        with self._session_factory() as session:
            user = session.scalar(select(User).where(User.telegram_chat_id == telegram_chat_id))
            if user is None:
                return {
                    "joined_at": None,
                    "total_orders": 0,
                    "active_orders": 0,
                    "delivered_orders": 0,
                    "failed_orders": 0,
                    "carriers_used": 0,
                }

            trackings = session.scalars(
                select(Tracking).where(Tracking.user_id == user.id)
            ).all()

            total_orders = len(trackings)
            active_orders = sum(1 for tracking in trackings if tracking.is_active)
            delivered_orders = sum(
                1 for tracking in trackings if tracking.last_status == TrackingStatus.DELIVERED.value
            )
            failed_orders = sum(
                1 for tracking in trackings if tracking.last_status == TrackingStatus.FAILED.value
            )
            carriers_used = len({tracking.carrier_id for tracking in trackings})

            return {
                "joined_at": user.created_at,
                "total_orders": total_orders,
                "active_orders": active_orders,
                "delivered_orders": delivered_orders,
                "failed_orders": failed_orders,
                "carriers_used": carriers_used,
            }

    def get_tracking_detail(self, telegram_chat_id: int, tracking_id: int) -> Tracking | None:
        with self._session_factory() as session:
            user = session.scalar(select(User).where(User.telegram_chat_id == telegram_chat_id))
            if user is None:
                return None

            return session.scalar(
                select(Tracking)
                .options(joinedload(Tracking.carrier))
                .where(
                    Tracking.id == tracking_id,
                    Tracking.user_id == user.id,
                )
            )

    def get_tracking_events(self, telegram_chat_id: int, tracking_id: int) -> list[TrackingEvent]:
        with self._session_factory() as session:
            user = session.scalar(select(User).where(User.telegram_chat_id == telegram_chat_id))
            if user is None:
                return []

            tracking = session.scalar(
                select(Tracking).where(
                    Tracking.id == tracking_id,
                    Tracking.user_id == user.id,
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
            user = session.scalar(select(User).where(User.telegram_chat_id == telegram_chat_id))
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
            session.commit()
            logger.info("Tracking removed: user=%s code=%s", telegram_chat_id, normalized_code)
            return True
