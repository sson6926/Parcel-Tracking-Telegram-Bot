from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, joinedload

from app.models import Carrier, Tracking, TrackingEvent, User
from app.providers import build_provider_registry
from app.providers.base import InvalidTrackingCodeError, TrackingProvider
from app.constants.enums import NotificationDTO, TrackingStatus

logger = logging.getLogger(__name__)

SUPPORTED_CARRIERS = {
    "jtexpress": "JT Express",
    "shopeeexpress": "Shopee Express",
    "ghn": "Giao Hàng Nhanh",
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
        """
        Auto-detect carrier from tracking code.
        
        Patterns:
        - Shopee: SPX*/SLS* (starts with SPX or SLS)
        - JT Express: JT* or pure digits (10-15 chars)
        - GHN: 8 uppercase alphanumeric chars (e.g., GYKEQFDX, GYWFRP6T)
        """
        code = tracking_code.strip().upper()
        
        # Shopee Express
        if code.startswith(("SPX", "SLS")):
            return "shopeeexpress"
        
        # JT Express
        if code.startswith("JT"):
            return "jtexpress"
        if code.isdigit() and 10 <= len(code) <= 15:
            return "jtexpress"
        
        # GHN: Exactly 8 alphanumeric chars (letters or mix of letters+digits)
        # Must have at least one letter to avoid pure digit codes
        if len(code) == 8 and code.isalnum() and any(c.isalpha() for c in code):
            return "ghn"
        
        return None

    @staticmethod
    def _is_valid_for_carrier(tracking_code: str, carrier_code: str) -> bool:
        """Validate tracking code format for specific carrier."""
        code = tracking_code.strip().upper()
        carrier = carrier_code.strip().lower()
        
        if carrier == "shopeeexpress":
            return code.startswith(("SPX", "SLS"))
        
        if carrier == "jtexpress":
            return code.startswith("JT") or (code.isdigit() and 10 <= len(code) <= 15)
        
        if carrier == "ghn":
            # GHN: Exactly 8 alphanumeric chars with at least one letter
            return len(code) == 8 and code.isalnum() and any(c.isalpha() for c in code)
        
        return True

    def seed_carriers(self) -> None:
        with self._session_factory() as session:
            existing = {row[0] for row in session.execute(select(Carrier.code)).all()}
            for code, name in SUPPORTED_CARRIERS.items():
                if code not in existing:
                    session.add(Carrier(code=code, name=name))
            session.execute(
                update(Tracking)
                .where(Tracking.last_status == TrackingStatus.DELIVERED.value)
                .values(is_active=False, next_check_at=None)
            )
            session.commit()
            logger.info("Carriers seeded: %s", list(SUPPORTED_CARRIERS.keys()))

    def _get_or_create_user(self, session: Session, telegram_chat_id: int) -> User:
        user = session.scalar(select(User).where(User.telegram_chat_id == telegram_chat_id))
        if user is None:
            user = User(telegram_chat_id=telegram_chat_id)
            session.add(user)
            session.flush()
        return user

    def ensure_user(
        self,
        telegram_chat_id: int,
        telegram_username: str | None = None,
        display_name: str | None = None,
    ) -> User:
        """Create a user record early so an administrator can grant permissions."""
        with self._session_factory() as session:
            user = self._get_or_create_user(session, telegram_chat_id)
            if telegram_username is not None:
                user.telegram_username = telegram_username
            if display_name:
                user.display_name = display_name
            session.commit()
            session.refresh(user)
            return user

    def is_admin(self, telegram_chat_id: int) -> bool:
        with self._session_factory() as session:
            return bool(session.scalar(
                select(User.is_admin).where(User.telegram_chat_id == telegram_chat_id)
            ))

    def get_admin_dashboard_stats(self) -> dict[str, int]:
        with self._session_factory() as session:
            return {
                "users": session.scalar(select(func.count(User.id))) or 0,
                "admins": session.scalar(
                    select(func.count(User.id)).where(User.is_admin.is_(True))
                ) or 0,
                "orders": session.scalar(select(func.count(Tracking.id))) or 0,
                "active_orders": session.scalar(
                    select(func.count(Tracking.id)).where(Tracking.is_active.is_(True))
                ) or 0,
                "delivered_orders": session.scalar(
                    select(func.count(Tracking.id)).where(
                        Tracking.last_status == TrackingStatus.DELIVERED.value
                    )
                ) or 0,
                "failed_orders": session.scalar(
                    select(func.count(Tracking.id)).where(
                        Tracking.last_status == TrackingStatus.FAILED.value
                    )
                ) or 0,
            }

    def admin_list_users(self, offset: int = 0, limit: int = 10) -> tuple[list[dict[str, object]], int]:
        with self._session_factory() as session:
            total = session.scalar(select(func.count(User.id))) or 0
            order_count = (
                select(Tracking.user_id, func.count(Tracking.id).label("order_count"))
                .group_by(Tracking.user_id)
                .subquery()
            )
            rows = session.execute(
                select(User, func.coalesce(order_count.c.order_count, 0))
                .outerjoin(order_count, order_count.c.user_id == User.id)
                .order_by(User.created_at.desc(), User.id.desc())
                .offset(offset)
                .limit(limit)
            ).all()
            return [
                {
                    "id": user.id,
                    "chat_id": user.telegram_chat_id,
                    "username": user.telegram_username,
                    "display_name": user.display_name,
                    "credits": user.credits,
                    "is_admin": user.is_admin,
                    "created_at": user.created_at,
                    "order_count": count,
                }
                for user, count in rows
            ], total

    def admin_get_broadcast_chat_ids(self) -> list[int]:
        with self._session_factory() as session:
            return list(session.scalars(
                select(User.telegram_chat_id).order_by(User.id.asc())
            ).all())

    def admin_get_user(self, user_id: int) -> dict[str, object] | None:
        with self._session_factory() as session:
            user = session.get(User, user_id)
            if user is None:
                return None
            total_orders = session.scalar(
                select(func.count(Tracking.id)).where(Tracking.user_id == user.id)
            ) or 0
            active_orders = session.scalar(
                select(func.count(Tracking.id)).where(
                    Tracking.user_id == user.id, Tracking.is_active.is_(True)
                )
            ) or 0
            return {
                "id": user.id,
                "chat_id": user.telegram_chat_id,
                "username": user.telegram_username,
                "display_name": user.display_name,
                "credits": user.credits,
                "is_admin": user.is_admin,
                "created_at": user.created_at,
                "order_count": total_orders,
                "active_order_count": active_orders,
            }

    def admin_toggle_user_admin(self, user_id: int) -> bool | None:
        with self._session_factory() as session:
            user = session.get(User, user_id)
            if user is None:
                return None
            user.is_admin = not user.is_admin
            session.commit()
            return user.is_admin

    def admin_list_orders(self, offset: int = 0, limit: int = 10) -> tuple[list[dict[str, object]], int]:
        with self._session_factory() as session:
            total = session.scalar(select(func.count(Tracking.id))) or 0
            rows = session.execute(
                select(Tracking, User.telegram_chat_id, Carrier.name)
                .join(User, Tracking.user_id == User.id)
                .join(Carrier, Tracking.carrier_id == Carrier.id)
                .order_by(Tracking.created_at.desc(), Tracking.id.desc())
                .offset(offset)
                .limit(limit)
            ).all()
            return [
                {
                    "id": tracking.id,
                    "tracking_code": tracking.tracking_code,
                    "status": tracking.last_status,
                    "is_active": tracking.is_active,
                    "chat_id": chat_id,
                    "carrier": carrier_name,
                    "created_at": tracking.created_at,
                }
                for tracking, chat_id, carrier_name in rows
            ], total

    def admin_get_order(self, tracking_id: int) -> dict[str, object] | None:
        with self._session_factory() as session:
            row = session.execute(
                select(Tracking, User.telegram_chat_id, Carrier.name)
                .join(User, Tracking.user_id == User.id)
                .join(Carrier, Tracking.carrier_id == Carrier.id)
                .where(Tracking.id == tracking_id)
            ).first()
            if row is None:
                return None
            tracking, chat_id, carrier_name = row
            event_count = session.scalar(
                select(func.count(TrackingEvent.id)).where(TrackingEvent.tracking_id == tracking.id)
            ) or 0
            return {
                "id": tracking.id,
                "tracking_code": tracking.tracking_code,
                "status": tracking.last_status,
                "is_active": tracking.is_active,
                "chat_id": chat_id,
                "carrier": carrier_name,
                "event_count": event_count,
                "created_at": tracking.created_at,
            }

    def admin_toggle_order_active(self, tracking_id: int) -> bool | None:
        with self._session_factory() as session:
            tracking = session.get(Tracking, tracking_id)
            if tracking is None:
                return None
            if tracking.last_status == TrackingStatus.DELIVERED.value:
                tracking.is_active = False
                tracking.next_check_at = None
                session.commit()
                return False
            tracking.is_active = not tracking.is_active
            if tracking.is_active:
                tracking.next_check_at = datetime.now(timezone.utc)
            session.commit()
            return tracking.is_active

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
        session.add(TrackingEvent(
            tracking_id=tracking.id,
            status=event.status.value,
            description=event.description,
            location=event.location,
            event_time=event.event_time,
            event_hash=event.event_hash,
        ))

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
        found_last_known = False

        for event in history:
            is_new = event.event_hash not in existing_hashes
            self._insert_event_if_new(session, tracking, event)
            existing_hashes.add(event.event_hash)
            
            # Mark that we've passed the last known event
            if last_known_hash and event.event_hash == last_known_hash:
                found_last_known = True
                continue
            
            # Only notify for events AFTER the last known event
            if notify and is_new and (last_known_hash is None or found_last_known):
                new_events.append(NotificationDTO(
                    tracking_code=tracking.tracking_code,
                    carrier_code=tracking.carrier.code,
                    status=event.status,
                    description=event.description,
                    location=event.location,
                    event_time=event.event_time,
                ))

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

    def add_tracking(self, telegram_chat_id: int, tracking_code: str, carrier_code_override: str | None = None) -> Tracking:
        normalized_code = tracking_code.strip().upper()
        if not normalized_code:
            raise ValueError("error.empty_tracking_code")

        carrier_code = carrier_code_override.lower() if carrier_code_override else self.detect_carrier(normalized_code)
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
                    self._sync_tracking_history(session, tracking, provider, require_history=require_history, notify=False)
                except InvalidTrackingCodeError:
                    raise ValueError("error.invalid_tracking_code")
                except Exception:
                    logger.exception("Initial sync failed for '%s'", normalized_code)

            session.commit()
            session.refresh(tracking)
            session.refresh(carrier)
            tracking.carrier = carrier
            logger.info("Tracking added: user=%s code=%s carrier=%s", telegram_chat_id, normalized_code, carrier_code)
            return tracking

    def get_user_credits(self, telegram_chat_id: int) -> int:
        with self._session_factory() as session:
            credits = session.scalar(
                select(User.credits).where(User.telegram_chat_id == telegram_chat_id)
            )
            return int(credits or 0)

    def list_trackings(self, telegram_chat_id: int) -> list[Tracking]:
        with self._session_factory() as session:
            user = session.scalar(select(User).where(User.telegram_chat_id == telegram_chat_id))
            if user is None:
                return []
            return list(session.scalars(
                select(Tracking)
                .options(joinedload(Tracking.carrier))
                .where(Tracking.user_id == user.id, Tracking.is_deleted.is_(False))
                .order_by(Tracking.created_at.desc())
            ).all())

    def get_user_profile_summary(self, telegram_chat_id: int) -> dict[str, object]:
        with self._session_factory() as session:
            user = session.scalar(select(User).where(User.telegram_chat_id == telegram_chat_id))
            if user is None:
                return {"joined_at": None, "credits": 0, "total_orders": 0, "active_orders": 0,
                        "delivered_orders": 0, "failed_orders": 0, "carriers_used": 0}

            trackings = session.scalars(select(Tracking).where(Tracking.user_id == user.id)).all()
            return {
                "joined_at": user.created_at,
                "credits": user.credits,
                "total_orders": len(trackings),
                "active_orders": sum(1 for t in trackings if t.is_active),
                "delivered_orders": sum(1 for t in trackings if t.last_status == TrackingStatus.DELIVERED.value),
                "failed_orders": sum(1 for t in trackings if t.last_status == TrackingStatus.FAILED.value),
                "carriers_used": len({t.carrier_id for t in trackings}),
            }

    def get_tracking_detail(self, telegram_chat_id: int, tracking_id: int) -> Tracking | None:
        with self._session_factory() as session:
            user = session.scalar(select(User).where(User.telegram_chat_id == telegram_chat_id))
            if user is None:
                return None
            return session.scalar(
                select(Tracking)
                .options(joinedload(Tracking.carrier))
                .where(Tracking.id == tracking_id, Tracking.user_id == user.id)
            )

    def toggle_tracking_notification(self, telegram_chat_id: int, tracking_id: int) -> bool | None:
        """Toggle notifications only when the tracking belongs to the requesting user."""
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

    def get_tracking_events(self, telegram_chat_id: int, tracking_id: int) -> list[TrackingEvent]:
        with self._session_factory() as session:
            user = session.scalar(select(User).where(User.telegram_chat_id == telegram_chat_id))
            if user is None:
                return []
            tracking = session.scalar(
                select(Tracking).where(Tracking.id == tracking_id, Tracking.user_id == user.id)
            )
            if tracking is None:
                return []
            return list(session.scalars(
                select(TrackingEvent)
                .where(TrackingEvent.tracking_id == tracking_id)
                .order_by(TrackingEvent.event_time.asc())
            ).all())

    def remove_tracking(self, telegram_chat_id: int, tracking_code: str) -> bool:
        normalized_code = tracking_code.strip().upper()
        with self._session_factory() as session:
            user = session.scalar(select(User).where(User.telegram_chat_id == telegram_chat_id))
            if user is None:
                return False
            tracking = session.scalar(
                select(Tracking).where(Tracking.user_id == user.id, Tracking.tracking_code == normalized_code)
            )
            if tracking is None:
                return False
            tracking.is_active = False
            tracking.is_deleted = True
            tracking.next_check_at = None
            session.commit()
            logger.info("Tracking removed: user=%s code=%s", telegram_chat_id, normalized_code)
            return True
