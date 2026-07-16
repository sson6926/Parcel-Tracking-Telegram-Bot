from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants.enums import TrackingStatus
from app.models import Carrier, Tracking, TrackingEvent, User

logger = logging.getLogger(__name__)


class AdminService:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    def get_dashboard_stats(self) -> dict[str, int]:
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

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    def list_users(
        self, offset: int = 0, limit: int = 10
    ) -> tuple[list[dict[str, object]], int]:
        with self._session_factory() as session:
            total = session.scalar(select(func.count(User.id))) or 0
            order_count_sub = (
                select(Tracking.user_id, func.count(Tracking.id).label("order_count"))
                .group_by(Tracking.user_id)
                .subquery()
            )
            rows = session.execute(
                select(User, func.coalesce(order_count_sub.c.order_count, 0))
                .outerjoin(order_count_sub, order_count_sub.c.user_id == User.id)
                .order_by(User.created_at.desc(), User.id.desc())
                .offset(offset)
                .limit(limit)
            ).all()
            users = [
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
            ]
            return users, total

    def get_broadcast_chat_ids(self) -> list[int]:
        with self._session_factory() as session:
            return list(
                session.scalars(
                    select(User.telegram_chat_id).order_by(User.id.asc())
                ).all()
            )

    def get_user(self, user_id: int) -> dict[str, object] | None:
        with self._session_factory() as session:
            user = session.get(User, user_id)
            if user is None:
                return None
            total_orders = (
                session.scalar(
                    select(func.count(Tracking.id)).where(Tracking.user_id == user.id)
                ) or 0
            )
            active_orders = (
                session.scalar(
                    select(func.count(Tracking.id)).where(
                        Tracking.user_id == user.id, Tracking.is_active.is_(True)
                    )
                ) or 0
            )
            return {
                "id": user.id,
                "chat_id": user.telegram_chat_id,
                "username": user.telegram_username,
                "display_name": user.display_name,
                "credits": user.credits,
                "is_admin": user.is_admin,
                "is_banned": user.is_banned,
                "created_at": user.created_at,
                "order_count": total_orders,
                "active_order_count": active_orders,
            }

    def toggle_user_admin(self, user_id: int) -> bool | None:
        with self._session_factory() as session:
            user = session.get(User, user_id)
            if user is None:
                return None
            user.is_admin = not user.is_admin
            session.commit()
            return user.is_admin

    def toggle_user_banned(self, user_id: int) -> bool | None:
        with self._session_factory() as session:
            user = session.get(User, user_id)
            if user is None:
                return None
            user.is_banned = not user.is_banned
            session.commit()
            return user.is_banned

    def adjust_user_credits(self, user_id: int, delta: int) -> int | None:
        """Add or subtract credits. Returns new balance, or None if user not found."""
        with self._session_factory() as session:
            user = session.get(User, user_id)
            if user is None:
                return None
            user.credits = max(0, user.credits + delta)
            session.commit()
            return user.credits

    def list_user_orders(
        self, user_id: int, offset: int = 0, limit: int = 10
    ) -> tuple[list[dict[str, object]], int]:
        with self._session_factory() as session:
            total = (
                session.scalar(
                    select(func.count(Tracking.id)).where(Tracking.user_id == user_id)
                ) or 0
            )
            rows = session.execute(
                select(Tracking, Carrier.name)
                .join(Carrier, Tracking.carrier_id == Carrier.id)
                .where(Tracking.user_id == user_id)
                .order_by(Tracking.created_at.desc(), Tracking.id.desc())
                .offset(offset)
                .limit(limit)
            ).all()
            orders = [
                {
                    "id": tracking.id,
                    "tracking_code": tracking.tracking_code,
                    "status": tracking.last_status,
                    "is_active": tracking.is_active,
                    "carrier": carrier_name,
                    "created_at": tracking.created_at,
                }
                for tracking, carrier_name in rows
            ]
            return orders, total

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    def list_orders(
        self, offset: int = 0, limit: int = 10
    ) -> tuple[list[dict[str, object]], int]:
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
            orders = [
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
            ]
            return orders, total

    def get_order(self, tracking_id: int) -> dict[str, object] | None:
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
            event_count = (
                session.scalar(
                    select(func.count(TrackingEvent.id)).where(
                        TrackingEvent.tracking_id == tracking.id
                    )
                ) or 0
            )
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

    def toggle_order_active(self, tracking_id: int) -> bool | None:
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
