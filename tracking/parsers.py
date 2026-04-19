from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from json import JSONDecodeError
from typing import Any

from tracking.types import TrackingStatus


@dataclass
class ParsedEvent:
    source_status: str
    normalized_status: TrackingStatus
    description: str
    location: str
    event_time: str | None


def extract_first_json_object(raw_text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()

    for index, char in enumerate(raw_text):
        if char != "{":
            continue

        try:
            parsed, _ = decoder.raw_decode(raw_text[index:])
            if isinstance(parsed, dict):
                return parsed
        except JSONDecodeError:
            continue

    raise ValueError("No JSON object found in input text.")


def normalize_status(source_status: str) -> TrackingStatus:
    status_text = source_status.strip().lower()

    # Failed/error states
    if "failed" in status_text or "that bai" in status_text:
        return TrackingStatus.FAILED
    if "lost" in status_text or "mat hang" in status_text:
        return TrackingStatus.FAILED
    if "unsuccessful" in status_text or "khong thanh cong" in status_text:
        return TrackingStatus.FAILED
    if "return" in status_text or "rts" in status_text or "tro lai" in status_text:
        return TrackingStatus.FAILED

    if "delivered" in status_text or "giao hang thanh cong" in status_text:
        return TrackingStatus.DELIVERED

    if "out for delivery" in status_text or "dang giao" in status_text:
        return TrackingStatus.OUT_FOR_DELIVERY

    if "picked" in status_text or "da lay" in status_text:
        return TrackingStatus.PICKED_UP

    if "transit" in status_text or "sorting" in status_text or "hub" in status_text:
        return TrackingStatus.IN_TRANSIT

    return TrackingStatus.CREATED


def normalize_shopee_record_status(record: dict[str, Any]) -> TrackingStatus:
    """
    Normalize Shopee Express status with priority:
    1. Check tracking_code for explicit failure indicators (most reliable for errors)
    2. Use milestone_name (most reliable for normal states)
    3. Fall back to milestone_code
    4. Parse description text as last resort
    """
    
    # Priority 1: Check tracking_code for explicit failure indicators
    tracking_code = str(record.get("tracking_code") or "").upper()
    if tracking_code:
        # Check for error/failed tracking codes (these override everything)
        if tracking_code.startswith("F96") or tracking_code.startswith("F97"):
            return TrackingStatus.FAILED
        if tracking_code in ("F650", "F651", "F659"):  # Delivery failed/attempted
            return TrackingStatus.FAILED
        if tracking_code.startswith("F67"):  # RTS (Return To Sender)
            return TrackingStatus.FAILED
    
    # Priority 2: Use milestone_name (most reliable for normal states)
    milestone_name = str(record.get("milestone_name") or "").strip().lower()
    if milestone_name:
        if "delivered" in milestone_name:
            return TrackingStatus.DELIVERED
        if "out for delivery" in milestone_name:
            return TrackingStatus.OUT_FOR_DELIVERY
        if "unsuccessful" in milestone_name or "failed" in milestone_name:
            return TrackingStatus.FAILED
        if "transit" in milestone_name:
            return TrackingStatus.IN_TRANSIT
        if "preparing" in milestone_name or "preparing to ship" in milestone_name:
            return TrackingStatus.CREATED
    
    # Priority 3: Check remaining tracking_code success cases
    if tracking_code:
        if tracking_code.startswith("F98"):
            return TrackingStatus.DELIVERED
        if tracking_code.startswith("F60") and not tracking_code.startswith("F65"):
            return TrackingStatus.OUT_FOR_DELIVERY
        if tracking_code.startswith("F44"):
            return TrackingStatus.PICKED_UP
    
    # Priority 4: Fall back to milestone_code
    milestone_code = record.get("milestone_code")
    if isinstance(milestone_code, int):
        if milestone_code == 10:
            return TrackingStatus.FAILED
        if milestone_code >= 8:
            return TrackingStatus.DELIVERED
        if milestone_code == 6:
            return TrackingStatus.OUT_FOR_DELIVERY
        if milestone_code == 5:
            return TrackingStatus.IN_TRANSIT
        if milestone_code in (3, 4):
            return TrackingStatus.PICKED_UP
        if milestone_code <= 2:
            return TrackingStatus.CREATED

    # Priority 5: Parse description text as last resort
    source_text = " ".join(
        [
            str(record.get("tracking_name") or ""),
            str(record.get("buyer_description") or ""),
            str(record.get("description") or ""),
        ]
    )
    return normalize_status(source_text)


def parse_shopeeexpress_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data", {})
    tracking_info = data.get("sls_tracking_info", {})
    records = tracking_info.get("records", [])

    parsed_events: list[ParsedEvent] = []
    for record in records:
        normalized = normalize_shopee_record_status(record)
        description = str(record.get("description") or "")
        location = ""

        current_location = record.get("current_location", {})
        if isinstance(current_location, dict):
            location = str(current_location.get("location_name") or "")

        event_time_unix = record.get("actual_time")
        event_time_str: str | None = None
        if event_time_unix and isinstance(event_time_unix, int):
            event_time_str = datetime.fromtimestamp(event_time_unix, tz=timezone.utc).isoformat()

        milestone_name = str(record.get("milestone_name") or "")
        parsed_events.append(
            ParsedEvent(
                source_status=milestone_name,
                normalized_status=normalized,
                description=description,
                location=location,
                event_time=event_time_str,
            )
        )

    return {
        "format": "shopeeexpress",
        "events": [
            {
                "source_status": e.source_status,
                "normalized_status": e.normalized_status.value,
                "description": e.description,
                "location": e.location,
                "event_time": e.event_time,
            }
            for e in parsed_events
        ],
    }


def detect_and_parse(raw_text: str) -> dict[str, Any]:
    try:
        payload = extract_first_json_object(raw_text)
    except ValueError:
        return {}

    if payload.get("format") == "shopeeexpress" or "sls_tracking_info" in payload.get("data", {}):
        return parse_shopeeexpress_payload(payload)

    return {}
