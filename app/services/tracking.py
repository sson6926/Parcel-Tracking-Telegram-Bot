"""
Facade that composes all sub-services.

External code continues to import `TrackingService` from this module (or from
`app.services`).  The class delegates to the focused sub-services so that
`tracking.py` stays thin and every concern lives in its own file.
"""
from __future__ import annotations

from typing import Callable

from sqlalchemy.orm import Session

from app.models import Tracking, TrackingEvent, User
from app.constants.enums import NotificationDTO
from app.providers.base import TrackingProvider

from app.services.carrier_service import (
    SUPPORTED_CARRIERS,
    detect_carrier,
    is_valid_for_carrier,
    seed_carriers,
)
from app.services.user_service import UserService
from app.services.admin_service import AdminService
from app.services.tracking_service import TrackingService as _CoreTrackingService


class TrackingService:
    """
    Unified service facade.

    Delegates to:
    - CarrierService utilities  (module-level functions in carrier_service.py)
    - UserService               (user management)
    - AdminService              (admin dashboard / management)
    - TrackingService (core)    (add / list / remove / events)
    """

    def __init__(
        self,
        session_factory: Callable[[], Session],
        check_interval_minutes: int = 5,
        provider_registry: dict[str, TrackingProvider] | None = None,
    ) -> None:
        self._session_factory = session_factory

        self._user_svc = UserService(session_factory)
        self._admin_svc = AdminService(session_factory)
        self._tracking_svc = _CoreTrackingService(
            session_factory,
            check_interval_minutes=check_interval_minutes,
            provider_registry=provider_registry,
        )

    # ------------------------------------------------------------------
    # Carrier helpers (kept as static/class-level for backward compat)
    # ------------------------------------------------------------------

    @staticmethod
    def detect_carrier(tracking_code: str) -> str | None:
        return detect_carrier(tracking_code)

    @staticmethod
    def _is_valid_for_carrier(tracking_code: str, carrier_code: str) -> bool:
        return is_valid_for_carrier(tracking_code, carrier_code)

    def seed_carriers(self) -> None:
        with self._session_factory() as session:
            seed_carriers(session)

    # ------------------------------------------------------------------
    # User service delegation
    # ------------------------------------------------------------------

    def ensure_user(
        self,
        telegram_chat_id: int,
        telegram_username: str | None = None,
        display_name: str | None = None,
    ) -> User:
        return self._user_svc.ensure_user(telegram_chat_id, telegram_username, display_name)

    def is_admin(self, telegram_chat_id: int) -> bool:
        return self._user_svc.is_admin(telegram_chat_id)

    def get_user_credits(self, telegram_chat_id: int) -> int:
        return self._user_svc.get_user_credits(telegram_chat_id)

    def get_user_profile_summary(self, telegram_chat_id: int) -> dict[str, object]:
        return self._user_svc.get_user_profile_summary(telegram_chat_id)

    # ------------------------------------------------------------------
    # Admin service delegation
    # ------------------------------------------------------------------

    def get_admin_dashboard_stats(self) -> dict[str, int]:
        return self._admin_svc.get_dashboard_stats()

    def admin_list_users(
        self, offset: int = 0, limit: int = 10
    ) -> tuple[list[dict[str, object]], int]:
        return self._admin_svc.list_users(offset, limit)

    def admin_get_broadcast_chat_ids(self) -> list[int]:
        return self._admin_svc.get_broadcast_chat_ids()

    def admin_get_user(self, user_id: int) -> dict[str, object] | None:
        return self._admin_svc.get_user(user_id)

    def admin_toggle_user_admin(self, user_id: int) -> bool | None:
        return self._admin_svc.toggle_user_admin(user_id)

    def admin_toggle_user_banned(self, user_id: int) -> bool | None:
        return self._admin_svc.toggle_user_banned(user_id)

    def admin_adjust_user_credits(self, user_id: int, delta: int) -> int | None:
        return self._admin_svc.adjust_user_credits(user_id, delta)

    def admin_list_user_orders(
        self, user_id: int, offset: int = 0, limit: int = 10
    ) -> tuple[list[dict[str, object]], int]:
        return self._admin_svc.list_user_orders(user_id, offset, limit)

    def admin_list_orders(
        self, offset: int = 0, limit: int = 10
    ) -> tuple[list[dict[str, object]], int]:
        return self._admin_svc.list_orders(offset, limit)

    def admin_get_order(self, tracking_id: int) -> dict[str, object] | None:
        return self._admin_svc.get_order(tracking_id)

    def admin_toggle_order_active(self, tracking_id: int) -> bool | None:
        return self._admin_svc.toggle_order_active(tracking_id)

    # ------------------------------------------------------------------
    # Core tracking service delegation
    # ------------------------------------------------------------------

    def _sync_tracking_history(
        self,
        session: Session,
        tracking: Tracking,
        provider: TrackingProvider,
        *,
        require_history: bool = False,
        notify: bool = True,
    ) -> list[NotificationDTO]:
        return self._tracking_svc._sync_tracking_history(
            session, tracking, provider,
            require_history=require_history,
            notify=notify,
        )

    def add_tracking(
        self,
        telegram_chat_id: int,
        tracking_code: str,
        carrier_code_override: str | None = None,
    ) -> Tracking:
        return self._tracking_svc.add_tracking(
            telegram_chat_id, tracking_code, carrier_code_override
        )

    def list_trackings(
        self, telegram_chat_id: int, status_filter: str | None = None
    ) -> list[Tracking]:
        return self._tracking_svc.list_trackings(telegram_chat_id, status_filter)

    def get_tracking_detail(
        self, telegram_chat_id: int, tracking_id: int
    ) -> Tracking | None:
        return self._tracking_svc.get_tracking_detail(telegram_chat_id, tracking_id)

    def toggle_tracking_notification(
        self, telegram_chat_id: int, tracking_id: int
    ) -> bool | None:
        return self._tracking_svc.toggle_tracking_notification(
            telegram_chat_id, tracking_id
        )

    def get_tracking_events(
        self, telegram_chat_id: int, tracking_id: int
    ) -> list[TrackingEvent]:
        return self._tracking_svc.get_tracking_events(telegram_chat_id, tracking_id)

    def remove_tracking(self, telegram_chat_id: int, tracking_code: str) -> bool:
        return self._tracking_svc.remove_tracking(telegram_chat_id, tracking_code)
