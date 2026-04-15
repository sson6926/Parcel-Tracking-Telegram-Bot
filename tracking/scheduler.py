import asyncio
import logging
from datetime import datetime, timedelta, timezone
from html import escape

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select
from sqlalchemy.orm import Session
from telegram import Bot
from telegram.error import TelegramError

from db.models import Tracking
from tracking.providers import build_provider_registry
from tracking.service import TrackingService
from tracking.types import TrackingStatus

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

    def start(self) -> None:
        self._scheduler.add_job(
            self._check_updates,
            "interval",
            minutes=5,
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
                select(Tracking).where(
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

                try:
                    new_events = self._service._sync_tracking_history(session, tracking, provider)
                    next_check = now + __import__(
                        "datetime",
                        fromlist=["timedelta"],
                    ).timedelta(minutes=5)
                    tracking.next_check_at = next_check
                    session.commit()
                    
                    # Send notifications for new events
                    if new_events and self._application:
                        self._send_notifications(tracking, new_events)
                        
                except Exception:
                    logger.exception("Failed to check tracking %d", tracking.id)

        logger.info("[Scheduler] Tick completed.")

    def _send_notifications(self, tracking: Tracking, new_events) -> None:
        """Send Telegram notifications for new tracking events."""
        if not self._application:
            logger.debug("Skipping notifications: application not available")
            return
        
        try:
            chat_id = tracking.user.telegram_chat_id
            bot = self._application.bot
            loop = self._application.loop
            
            if not bot or not loop:
                logger.debug("Skipping notifications: bot or loop not available")
                return
            
            for event in new_events:
                message = self._format_notification_message(tracking, event)
                
                try:
                    # Schedule coroutine in the application's event loop
                    future = asyncio.run_coroutine_threadsafe(
                        bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            parse_mode="HTML",
                        ),
                        loop
                    )
                    # Wait briefly for the result (with timeout)
                    future.result(timeout=5)
                    logger.info(f"Notification sent to chat {chat_id}")
                except TelegramError as e:
                    logger.warning(f"Failed to send notification to chat {chat_id}: {e}")
                except TimeoutError:
                    logger.warning(f"Timeout sending notification to chat {chat_id}")
        except Exception:
            logger.exception("Failed to send notifications")

    @staticmethod
    def _format_notification_message(tracking: Tracking, event) -> str:
        """Format notification message for Telegram."""
        from datetime import timezone, timedelta
        
        # Convert to local timezone (UTC+7 for Vietnam)
        local_tz = timezone(timedelta(hours=7))
        event_time = event.event_time.astimezone(local_tz) if event.event_time.tzinfo else event.event_time
        time_str = event_time.strftime("%d/%m/%Y %H:%M")
        
        # Status emoji based on event status
        status_emoji = {
            "CREATED": "🆕",
            "PICKED_UP": "📥",
            "IN_TRANSIT": "🚚",
            "OUT_FOR_DELIVERY": "🛵",
            "DELIVERED": "✅",
            "FAILED": "❌",
        }.get(event.status.value if hasattr(event.status, 'value') else str(event.status), "📦")
        
        # Escape HTML special characters
        tracking_code = escape(tracking.tracking_code)
        carrier_name = escape(tracking.carrier.name)
        status_str = escape(event.status.value if hasattr(event.status, 'value') else str(event.status))
        description = escape(event.description or "")
        location = escape(event.location or "")
        
        message = f"""{status_emoji} <b>Cập nhật đơn hàng</b>

<b>Mã vận chuyển:</b> <code>{tracking_code}</code>
<b>Nhà vận chuyển:</b> {carrier_name}
<b>Trạng thái:</b> {status_str}
<b>Thời gian:</b> {time_str}"""
        
        if description:
            message += f"\n<b>Chi tiết:</b> {description}"
        
        if location:
            message += f"\n<b>Địa điểm:</b> {location}"
        
        return message
