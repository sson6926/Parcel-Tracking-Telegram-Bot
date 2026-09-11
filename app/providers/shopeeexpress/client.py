from __future__ import annotations

from datetime import datetime, timezone
import logging
from time import perf_counter
from typing import Any

import httpx

from app.providers.shopeeexpress.parser import detect_and_parse
from app.providers.base import InvalidTrackingCodeError, TrackingProvider, compute_event_hash
from app.constants.enums import TrackingEventDTO, TrackingStatus

logger = logging.getLogger(__name__)


class ShopeeExpressProvider(TrackingProvider):
    carrier_code = "shopeeexpress"
    _DEFAULT_API_URL = "https://spx.vn/shipment/order/open/order/get_order_info"

    def __init__(self, timeout_seconds: float = 12.0, api_url: str = _DEFAULT_API_URL) -> None:
        self._timeout_seconds = timeout_seconds
        self._api_url = api_url
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=self._timeout_seconds)
        return self._client

    def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            self._client.close()

    def fetch_latest_event(self, tracking_code: str, current_status: TrackingStatus | None) -> TrackingEventDTO:
        history = self.fetch_event_history(tracking_code)
        if history:
            return history[-1]
        status = TrackingStatus.CREATED
        description = "Shopee Express: da tiep nhan thong tin van don"
        event_time = datetime.now(timezone.utc)
        return TrackingEventDTO(
            status=status,
            description=description,
            location="",
            event_time=event_time,
            event_hash=compute_event_hash(tracking_code, status, description, "", event_time.isoformat()),
        )

    def fetch_event_history(self, tracking_code: str) -> list[TrackingEventDTO]:
        payload = self._fetch_live_payload(tracking_code)
        if not payload or payload.get("format") != "shopeeexpress":
            return []

        events = payload.get("events") or []
        candidates: list[TrackingEventDTO] = []

        for row in events:
            try:
                status = TrackingStatus(str(row.get("normalized_status") or TrackingStatus.CREATED.value))
            except ValueError:
                status = TrackingStatus.CREATED

            description = str(row.get("description") or "Shopee Express update")
            location = str(row.get("location") or "")
            event_time = datetime.now(timezone.utc)
            event_time_str = row.get("event_time")

            if event_time_str:
                try:
                    event_time = datetime.fromisoformat(str(event_time_str))
                except ValueError:
                    pass

            candidates.append(TrackingEventDTO(
                status=status,
                description=description,
                location=location,
                event_time=event_time,
                event_hash=compute_event_hash(tracking_code, status, description, location, event_time.isoformat()),
            ))

        candidates.sort(key=lambda item: item.event_time)
        return candidates

    def _fetch_live_payload(self, tracking_code: str) -> dict[str, Any] | None:
        params = {"spx_tn": tracking_code, "language_code": "vi"}
        headers = {
            "accept": "application/json, text/plain, */*",
            "referer": f"https://spx.vn/track?{tracking_code}",
            "user-agent": "Mozilla/5.0",
        }

        try:
            started_at = perf_counter()
            logger.debug("Shopee API request start: tracking_code=%s", tracking_code)
            client = self._get_client()
            response = client.get(self._api_url, params=params, headers=headers)
            elapsed_ms = int((perf_counter() - started_at) * 1000)
            logger.debug("Shopee API response: tracking_code=%s status=%s elapsed_ms=%s",
                         tracking_code, response.status_code, elapsed_ms)

            if response.status_code != 200:
                return None

            payload = response.json()
            if self._is_invalid_tracking_response(payload):
                raise InvalidTrackingCodeError(f"Invalid Shopee tracking code: {tracking_code}")

            if payload.get("retcode") != 0:
                return None

            return detect_and_parse(response.text)
        except InvalidTrackingCodeError:
            raise
        except Exception:
            logger.exception("Failed to fetch live Shopee status for %s", tracking_code)
            return None

    @staticmethod
    def _is_invalid_tracking_response(payload: dict[str, Any]) -> bool:
        retcode = payload.get("retcode")
        if retcode == -1000:
            return True
        message = str(payload.get("message") or "").lower()
        invalid_markers = ("retcode:-2023002", "get logistic order index map error", "ref record not unique")
        return retcode == 2 and any(marker in message for marker in invalid_markers)
