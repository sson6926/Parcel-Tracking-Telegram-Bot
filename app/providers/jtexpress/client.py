from __future__ import annotations

from datetime import datetime, timezone
import logging
from time import perf_counter

import httpx

from app.providers.base import TrackingProvider, compute_event_hash, InvalidTrackingCodeError
from app.constants.enums import TrackingEventDTO, TrackingStatus
from app.providers.jtexpress.parser import (
    parse_tracking_events,
    parse_datetime,
    detect_status_from_description,
)

logger = logging.getLogger(__name__)


class JTExpressProvider(TrackingProvider):
    carrier_code = "jtexpress"
    _tracking_url = "https://jtexpress.vn/vi/tracking"
    _timeout_seconds = 10
    
    @staticmethod
    def parse_tracking_code(tracking_code: str) -> tuple[str, str | None]:
        """
        Parse JT Express tracking code format.
        
        Supports:
        - JT123456789 -> (JT123456789, None)
        - 1234567890 -> (1234567890, None)  
        - JT123456789-1234 -> (JT123456789, 1234)
        - 1234567890-5678 -> (1234567890, 5678)
        
        Returns:
            (order_code, phone_digits) where phone_digits is None or 4 digits
        
        Raises:
            InvalidTrackingCodeError: if format is invalid
        """
        code = tracking_code.strip().upper()
        
        if "-" not in code:
            # Standard format without phone digits
            return (code, None)
        
        # Format with phone digits: code-phone4digits
        parts = code.split("-", 1)
        if len(parts) != 2:
            raise InvalidTrackingCodeError(f"Invalid JT Express format: {tracking_code}")
        
        order_code, phone_part = parts
        
        # Validate phone digits: must be exactly 4 digits
        if not phone_part.isdigit() or len(phone_part) != 4:
            raise InvalidTrackingCodeError(
                f"Phone digits must be exactly 4 digits, got: {phone_part}"
            )
        
        return (order_code, phone_part)

    def fetch_latest_event(self, tracking_code: str, current_status: TrackingStatus | None) -> TrackingEventDTO:
        """Fetch latest tracking event. Auto-parses tracking_code to extract phone digits if present."""
        history = self.fetch_event_history(tracking_code)
        if history:
            return history[-1]
        # This should never happen since fetch_event_history raises on error
        raise ValueError("No tracking events found")

    def fetch_event_history(self, tracking_code: str) -> list[TrackingEventDTO]:
        """Fetch tracking history. Auto-parses tracking_code to extract phone digits if present."""
        order_code, phone_digits = self.parse_tracking_code(tracking_code)
        html = self._fetch_tracking_html(order_code, phone_digits)
        raw_events = parse_tracking_events(html)

        if not raw_events:
            raise ValueError("No tracking events found for this order")
        
        events: list[TrackingEventDTO] = []
        for raw_event in raw_events:
            event_time = parse_datetime(raw_event.date_str, raw_event.time_str)
            status = detect_status_from_description(raw_event.description)
            
            events.append(TrackingEventDTO(
                status=status,
                description=raw_event.description,
                location="",
                event_time=event_time,
                event_hash=compute_event_hash(
                    tracking_code,
                    status,
                    raw_event.description,
                    "",
                    event_time.isoformat()
                ),
            ))
        
        return events

    def _fetch_tracking_html(self, tracking_code: str, phone_digits: str | None = None) -> str:
        """Fetch HTML page from JT Express tracking website."""
        try:
            started_at = perf_counter()
            logger.debug("JT page request start: tracking_code=%s phone_digits=%s", tracking_code, phone_digits)
            
            params = {
                "type": "track",
                "billcode": tracking_code,
            }
            
            if phone_digits:
                params["cellphone"] = phone_digits
            
            headers = {
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "vi,en-US;q=0.9,en;q=0.8",
                "Referer": f"https://jtexpress.vn/vi/tracking?type=track",
            }
            
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.get(
                    self._tracking_url,
                    params=params,
                    headers=headers,
                    follow_redirects=True,
                )
            
            elapsed_ms = int((perf_counter() - started_at) * 1000)
            logger.debug("JT page response: tracking_code=%s status=%s elapsed_ms=%s",
                         tracking_code, response.status_code, elapsed_ms)
            
            html = response.text
            
            # Check if tracking code is not found
            html_lower = html.lower()
            if "không tìm thấy" in html_lower or "vận đơn không tồn tại" in html_lower:
                raise InvalidTrackingCodeError(f"Tracking code not found: {tracking_code}")
            
            return html
                
        except httpx.HTTPError as e:
            logger.warning("HTTP error fetching JT Express HTML for %s: %s", tracking_code, str(e))
            raise
        except InvalidTrackingCodeError:
            raise
        except Exception as e:
            logger.warning("Failed to fetch JT Express HTML for %s: %s", tracking_code, str(e))
            raise
