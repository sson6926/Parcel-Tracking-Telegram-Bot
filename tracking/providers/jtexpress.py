from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from time import perf_counter

import httpx

from tracking.providers.base import TrackingProvider, compute_event_hash
from tracking.types import TrackingEventDTO, TrackingStatus

logger = logging.getLogger(__name__)

_FLOW: list[tuple[TrackingStatus, str]] = [
    (TrackingStatus.CREATED, "Đã tiếp nhận vận đơn"),
    (TrackingStatus.PICKED_UP, "Đã lấy hàng"),
    (TrackingStatus.IN_TRANSIT, "Đang vận chuyển"),
    (TrackingStatus.OUT_FOR_DELIVERY, "Đang giao hàng"),
    (TrackingStatus.DELIVERED, "Đã giao thành công"),
]


class JTExpressProvider(TrackingProvider):
    carrier_code = "jtexpress"
    _tracking_url = "https://www.jte.vn/dang-ky-van-don"
    _timeout_seconds = 10

    def fetch_latest_event(
        self,
        tracking_code: str,
        current_status: TrackingStatus | None,
    ) -> TrackingEventDTO:
        history = self.fetch_event_history(tracking_code)
        if history:
            return history[-1]

        status = TrackingStatus.IN_TRANSIT
        description = "JT Express: Vận đơn đang theo dõi"
        location = ""
        event_time = datetime.now(timezone.utc)
        event_hash = compute_event_hash(tracking_code, status, description, location, event_time.isoformat())
        return TrackingEventDTO(
            status=status,
            description=description,
            location=location,
            event_time=event_time,
            event_hash=event_hash,
        )

    def fetch_event_history(self, tracking_code: str) -> list[TrackingEventDTO]:
        detected_status = self._detect_status_from_html(tracking_code)
        now = datetime.now(timezone.utc)
        events: list[TrackingEventDTO] = []

        for idx, (flow_status, flow_desc) in enumerate(_FLOW):
            event_time = now - timedelta(hours=len(_FLOW) - idx)
            event_hash = compute_event_hash(tracking_code, flow_status, flow_desc, "", event_time.isoformat())
            events.append(
                TrackingEventDTO(
                    status=flow_status,
                    description=flow_desc,
                    location="",
                    event_time=event_time,
                    event_hash=event_hash,
                )
            )

        if detected_status != TrackingStatus.IN_TRANSIT and events[-1].status != detected_status:
            description = "Cập nhật trạng thái vận đơn"
            events[-1] = TrackingEventDTO(
                status=detected_status,
                description=description,
                location="",
                event_time=now,
                event_hash=compute_event_hash(tracking_code, detected_status, description, "", now.isoformat()),
            )

        return events

    def _detect_status_from_html(self, tracking_code: str) -> TrackingStatus:
        try:
            started_at = perf_counter()
            logger.debug("JT page request start: tracking_code=%s", tracking_code)
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.get(self._tracking_url, headers={"user-agent": "Mozilla/5.0"})
            elapsed_ms = int((perf_counter() - started_at) * 1000)
            logger.debug(
                "JT page response: tracking_code=%s status=%s elapsed_ms=%s",
                tracking_code,
                response.status_code,
                elapsed_ms,
            )

            html = response.text.lower()
            if "giao hang thanh cong" in html or "da giao" in html:
                logger.debug("JT detected status DELIVERED for %s", tracking_code)
                return TrackingStatus.DELIVERED
            if "dang giao" in html:
                logger.debug("JT detected status OUT_FOR_DELIVERY for %s", tracking_code)
                return TrackingStatus.OUT_FOR_DELIVERY
        except Exception:
            logger.warning("Failed to fetch JT Express status for %s", tracking_code)

        logger.debug("JT fallback status IN_TRANSIT for %s", tracking_code)
        return TrackingStatus.IN_TRANSIT
