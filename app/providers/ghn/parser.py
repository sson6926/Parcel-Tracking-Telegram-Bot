"""GHN response parser."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from app.constants.enums import TrackingStatus

logger = logging.getLogger(__name__)


def normalize_status(status: str, action_code: str | None = None) -> TrackingStatus:
    """
    Normalize GHN status to TrackingStatus enum.
    
    GHN Status Flow:
    - ready_to_pick → picking → picked → storing → transporting → delivering → delivered
    - Or: → delivery_fail → waiting_to_return → return → returning → returned
    """
    status_lower = status.lower()
    
    # Final states - Delivered/Returned
    if status_lower == "delivered":
        return TrackingStatus.DELIVERED
    if status_lower == "returned":
        return TrackingStatus.DELIVERED  # Successfully returned to sender
    
    # Failed states
    if status_lower in ("delivery_fail", "cancel", "exception"):
        return TrackingStatus.FAILED
    if status_lower == "waiting_to_return":
        return TrackingStatus.FAILED  # Waiting confirmation to return = failed delivery
    
    # Out for delivery
    if status_lower in ("delivering", "returning"):
        return TrackingStatus.OUT_FOR_DELIVERY
    
    # Picked up
    if status_lower == "picked":
        return TrackingStatus.PICKED_UP
    
    # In transit (various warehouse/sorting states)
    if status_lower in ("transporting", "return_transporting"):
        return TrackingStatus.IN_TRANSIT
    if status_lower == "storing":
        return TrackingStatus.IN_TRANSIT
    if status_lower in ("picking", "picked_to_storing", "delivery_fail_to_storing"):
        return TrackingStatus.IN_TRANSIT
    
    # Created/Ready states
    if status_lower in ("ready_to_pick", "return"):
        return TrackingStatus.CREATED
    
    # Default to CREATED for unknown statuses
    logger.warning("Unknown GHN status: %s (action_code: %s)", status, action_code)
    return TrackingStatus.CREATED


def parse_event_time(action_at: str | None) -> datetime:
    """Parse GHN event time string to datetime."""
    if not action_at:
        return datetime.now(timezone.utc)
    
    try:
        # GHN uses ISO format with Z suffix
        # Handle milliseconds that may be 1-3 digits (e.g., .17Z, .170Z, .1Z)
        time_str = action_at.replace("Z", "+00:00")
        
        # Normalize milliseconds to 6 digits for microseconds
        if "." in time_str:
            parts = time_str.split(".")
            if len(parts) == 2:
                base_time = parts[0]
                fractional_and_tz = parts[1]
                # Extract fractional seconds and timezone
                if "+" in fractional_and_tz:
                    fractional, tz = fractional_and_tz.split("+")
                    # Pad fractional seconds to 6 digits (microseconds)
                    fractional = fractional.ljust(6, "0")
                    time_str = f"{base_time}.{fractional}+{tz}"
        
        return datetime.fromisoformat(time_str)
    except (ValueError, AttributeError) as e:
        logger.warning("Failed to parse GHN time '%s': %s", action_at, e)
        return datetime.now(timezone.utc)


def parse_location(location_data: dict | None) -> str:
    """Extract location address from GHN location object."""
    if not location_data or not isinstance(location_data, dict):
        return ""
    
    return location_data.get("address", "")


def build_description(log: dict) -> str:
    """Build event description from GHN log entry."""
    status_name = log.get("status_name", "")
    reason = log.get("reason")
    
    if reason:
        return f"{status_name} - {reason}"
    
    return status_name


def parse_tracking_response(data: dict) -> dict:
    """
    Parse GHN API response into structured format.
    
    Args:
        data: Raw API response from GHN
        
    Returns:
        dict with:
            - order_info: Order metadata
            - events: List of parsed tracking events
            
    Raises:
        ValueError: If response is invalid or order not found
    """
    code = data.get("code")
    
    # Handle error responses
    if code == 400:
        code_message = data.get("code_message", "")
        if code_message == "ORDER_NOT_FOUND":
            raise ValueError("Order not found")
        raise ValueError(f"GHN API error: {data.get('message', 'Unknown error')}")
    
    if code != 200:
        raise ValueError(f"GHN API error: {data.get('message', 'Unknown error')}")
    
    response_data = data.get("data", {})
    if not response_data:
        raise ValueError("No data in response")
    
    order_info = response_data.get("order_info", {})
    tracking_logs = response_data.get("tracking_logs", [])
    
    if not tracking_logs:
        raise ValueError("No tracking logs found")
    
    parsed_events = []
    for log in tracking_logs:
        status = log.get("status", "")
        action_code = log.get("action_code")
        
        parsed_events.append({
            "status": status,
            "action_code": action_code,
            "normalized_status": normalize_status(status, action_code),
            "status_name": log.get("status_name", ""),
            "description": build_description(log),
            "location": parse_location(log.get("location")),
            "event_time": parse_event_time(log.get("action_at")),
            "reason": log.get("reason"),
            "reason_code": log.get("reason_code"),
        })
    
    return {
        "order_code": order_info.get("order_code"),
        "order_status": order_info.get("status"),
        "status_name": order_info.get("status_name"),
        "events": parsed_events,
    }
