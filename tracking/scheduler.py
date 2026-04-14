import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select
from sqlalchemy.orm import Session

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
    ) -> None:
        self._session_factory = session_factory
        self._service = service
        self._scheduler = BackgroundScheduler()
        self._provider_registry = build_provider_registry()

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

            for tracking in trackings:
                provider = self._provider_registry.get(tracking.carrier.code)
                if provider is None:
                    continue

                try:
                    self._service._sync_tracking_history(session, tracking, provider)
                    next_check = now + __import__(
                        "datetime",
                        fromlist=["timedelta"],
                    ).timedelta(minutes=5)
                    tracking.next_check_at = next_check
                    session.commit()
                except Exception:
                    logger.exception("Failed to check tracking %d", tracking.id)

        logger.debug("Tracking check_updates completed")
