import asyncio
import logging
from datetime import datetime, timedelta, timezone
from html import escape

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from telegram.error import TelegramError

from db.models import Tracking
from tracking.constants import (
    DEFAULT_STATUS_ICON,
    DISPLAY_TIMEZONE,
    NOTIFICATION_TIMEOUT_SECONDS,
    STATUS_ICONS,
    TRACKING_CHECK_INTERVAL_MINUTES,
)
from tracking.providers import build_provider_registry
from tracking.service import TrackingService
from tracking.types import NotificationDTO

logger = logging.getLogger(__name__)


class TrackingScheduler:
    def __init__(
        self,
        session_factory,
        service: TrackingService,
        application=None,
    ) -> None:
        self._session_factory = session_factory
        self._service = service
        self._scheduler = BackgroundScheduler()
        self._provider_registry = build_provider_registry()
        self._application = application
        self._event_loop = None  # set after application starts

    def set_event_loop(self, loop) -> None:
        self._event_loop = loop

    def start(self) -> None:
        self._scheduler.add_job(
            self._check_updates,
            "interval",
            minutes=TRACKING_CHECK_INTERVAL_MINUTES,
            id="tracking_check_updates",
            replace_existing=True,
        )
        self._scheduler.start()
        logger.info("TrackingScheduler started")

    def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
        logger.info("TrackingScheduler stopped")

    def _check_updates(self) -> None:
        with self._session_factory() as session:
            now = datetime.now(timezone.utc)
            trackings = session.scalars(
                select(Tracking)
                .options(joinedload(Tracking.user), joinedload(Tracking.carrier))
                .where(
                    Tracking.is_active.is_(True),
                    (Tracking.next_check_at.is_(None)) | (Tracking.next_check_at <= now),
                )
            ).all()

            logger.info(
                "[Scheduler] %s: Checking %d active orders for update...",
                now.strftime("%Y-%m-%d %H:%M:%S"),
                len(trackings),
            )

            for tracking in trackings:
                provider = self._provider_registry.get(tracking.carrier.code)
                if provider is None:
                    continue

                # Extract data before commit to avoid detached instance errors
                chat_id = tracking.user.telegram_chat_id
                carrier_name = tracking.carrier.name
                tracking_code = tracking.tracking_code

                try:
                    new_events = self._service._sync_tracking_history(session, tracking, provider)
                    tracking.next_check_at = now + timedelta(minutes=TRACKING_CHECK_INTERVAL_MINUTES)
                    session.commit()

                    if new_events and self._application:
                        self._send_notifications(
                            chat_id=chat_id,
                            carrier_name=carrier_name,
                            tracking_code=tracking_code,
                            new_events=new_events,
                        )

                except Exception:
                    logger.exception("Failed to check tracking %d", tracking.id)

        logger.info("[Scheduler] Tick completed.")

    def _send_notifications(
        self,
        chat_id: int,
        carrier_name: str,
        tracking_code: str,
        new_events: list[NotificationDTO],
    ) -> None:
        if not self._application:
            logger.debug("Skipping notifications: application not available")
            return

        loop = self._event_loop
        if loop is None or not loop.is_running():
            logger.warning("Skipping notifications: event loop not available")
            return

        bot = self._application.bot

        for event in new_events:
            message = self._format_notification_message(
                tracking_code=tracking_code,
                carrier_name=carrier_name,
                event=event,
            )
            try:
                future = asyncio.run_coroutine_threadsafe(
                    bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode="HTML",
                    ),
                    loop,
                )
                future.result(timeout=NOTIFICATION_TIMEOUT_SECONDS)
                logger.info("Notification sent to chat %s for %s", chat_id, tracking_code)
            except TelegramError as e:
                logger.warning("Failed to send notification to chat %s: %s", chat_id, e)
            except TimeoutError:
                logger.warning("Timeout sending notification to chat %s", chat_id)
            except Exception:
                logger.exception("Unexpected error sending notification to chat %s", chat_id)

    @staticmethod
    def _format_notification_message(
        tracking_code: str,
        carrier_name: str,
        event: NotificationDTO,
    ) -> str:
        event_time = event.event_time
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        time_str = event_time.astimezone(DISPLAY_TIMEZONE).strftime("%d/%m/%Y %H:%M")

        status_emoji = STATUS_ICONS.get(event.status.value, DEFAULT_STATUS_ICON)
        tracking_code_esc = escape(tracking_code)
        carrier_name_esc = escape(carrier_name)
        status_str = escape(event.status.value)
        description = escape(event.description or "")
        location = escape(event.location or "")

        message = (
            f"{status_emoji} <b>Cập nhật đơn hàng</b>\n\n"
            f"<b>Mã vận chuyển:</b> <code>{tracking_code_esc}</code>\n"
            f"<b>Nhà vận chuyển:</b> {carrier_name_esc}\n"
            f"<b>Trạng thái:</b> {status_str}\n"
            f"<b>Thời gian:</b> {time_str}"
        )

        if description:
            message += f"\n<b>Chi tiết:</b> {description}"
        if location:
            message += f"\n<b>Địa điểm:</b> {location}"

        return message
