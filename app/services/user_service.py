from __future__ import annotations

import logging
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants.enums import TrackingStatus
from app.models import Tracking, User

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def get_or_create_user(self, session: Session, telegram_chat_id: int) -> User:
        user = session.scalar(select(User).where(User.telegram_chat_id == telegram_chat_id))
        if user is None:
            user = User(telegram_chat_id=telegram_chat_id)
            session.add(user)
            session.flush()
        return user

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ensure_user(
        self,
        telegram_chat_id: int,
        telegram_username: str | None = None,
        display_name: str | None = None,
    ) -> User:
        """Upsert a user record so admins can grant permissions early."""
        with self._session_factory() as session:
            user = self.get_or_create_user(session, telegram_chat_id)
            if telegram_username is not None:
                user.telegram_username = telegram_username
            if display_name:
                user.display_name = display_name
            session.commit()
            session.refresh(user)
            return user

    def is_admin(self, telegram_chat_id: int) -> bool:
        with self._session_factory() as session:
            return bool(
                session.scalar(
                    select(User.is_admin).where(User.telegram_chat_id == telegram_chat_id)
                )
            )

    def get_user_credits(self, telegram_chat_id: int) -> int:
        with self._session_factory() as session:
            credits = session.scalar(
                select(User.credits).where(User.telegram_chat_id == telegram_chat_id)
            )
            return int(credits or 0)

    def get_user_profile_summary(self, telegram_chat_id: int) -> dict[str, object]:
        with self._session_factory() as session:
            user = session.scalar(
                select(User).where(User.telegram_chat_id == telegram_chat_id)
            )
            if user is None:
                return {
                    "joined_at": None,
                    "credits": 0,
                    "total_orders": 0,
                    "active_orders": 0,
                    "delivered_orders": 0,
                    "failed_orders": 0,
                    "carriers_used": 0,
                }

            trackings = session.scalars(
                select(Tracking).where(Tracking.user_id == user.id)
            ).all()
            return {
                "joined_at": user.created_at,
                "credits": user.credits,
                "total_orders": len(trackings),
                "active_orders": sum(1 for t in trackings if t.is_active),
                "delivered_orders": sum(
                    1 for t in trackings if t.last_status == TrackingStatus.DELIVERED.value
                ),
                "failed_orders": sum(
                    1 for t in trackings if t.last_status == TrackingStatus.FAILED.value
                ),
                "carriers_used": len({t.carrier_id for t in trackings}),
            }
