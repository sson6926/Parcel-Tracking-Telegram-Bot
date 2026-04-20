"""GHN (Giao Hàng Nhanh) provider."""
from __future__ import annotations

import logging

import httpx

from app.providers.base import InvalidTrackingCodeError, TrackingProvider, compute_event_hash
from app.providers.ghn.parser import parse_tracking_response
from app.constants.enums import TrackingEventDTO

logger = logging.getLogger(__name__)

GHN_API_URL = "https://fe-online-gateway.ghn.vn/order-tracking/public-api/client/tracking-logs"
GHN_HEADERS = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "origin": "https://donhang.ghn.vn",
    "referer": "https://donhang.ghn.vn/",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


class GHNProvider(TrackingProvider):
    """Provider for GHN (Giao Hàng Nhanh) tracking."""

    carrier_code = "ghn"

    def fetch_event_history(self, tracking_code: str) -> list[TrackingEventDTO]:
        """Fetch tracking history from GHN API."""
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    GHN_API_URL,
                    headers=GHN_HEADERS,
                    json={"order_code": tracking_code},
                )
                
                # GHN returns 200 even for errors, check response body
                data = response.json()
                
                # Don't raise_for_status() - GHN uses 200 for errors too
                # Parser will handle error codes in response body

            # Parse response using parser module
            parsed = parse_tracking_response(data)
            
            events = []
            for event_data in parsed["events"]:
                # event_data["normalized_status"] is already a TrackingStatus enum
                event_hash = compute_event_hash(
                    tracking_code=tracking_code,
                    status=event_data["normalized_status"],  # This is TrackingStatus enum
                    description=event_data["description"],
                    location=event_data["location"],
                    event_time=event_data["event_time"].isoformat() if event_data["event_time"] else None,
                )

                events.append(TrackingEventDTO(
                    status=event_data["normalized_status"],
                    description=event_data["description"],
                    location=event_data["location"],
                    event_time=event_data["event_time"],
                    event_hash=event_hash,
                ))

            return events

        except ValueError as e:
            # Parser raised ValueError for invalid/not found orders
            logger.warning("GHN parser error for %s: %s", tracking_code, e)
            raise InvalidTrackingCodeError(f"Invalid tracking code: {tracking_code}")
        except httpx.HTTPStatusError as e:
            logger.error("GHN API HTTP error for %s: %s", tracking_code, e)
            raise InvalidTrackingCodeError(f"Failed to fetch tracking: {tracking_code}")
        except httpx.RequestError as e:
            logger.error("GHN API request error for %s: %s", tracking_code, e)
            raise InvalidTrackingCodeError(f"Network error: {tracking_code}")
        except Exception as e:
            logger.exception("Unexpected error fetching GHN tracking %s", tracking_code)
            raise InvalidTrackingCodeError(f"Error fetching tracking: {tracking_code}")

    def fetch_latest_event(
        self,
        tracking_code: str,
        current_status: TrackingStatus | None = None,
    ) -> TrackingEventDTO:
        """Fetch latest event (GHN always returns full history)."""
        history = self.fetch_event_history(tracking_code)
        return history[-1] if history else None

