"""JT Express HTML parser for tracking events."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import NamedTuple

from app.constants.enums import TrackingStatus


class JTEventRaw(NamedTuple):
    """Raw event data parsed from HTML."""
    time_str: str    # e.g., "08:41:52"
    date_str: str    # e.g., "2026-07-13"
    description: str


# ---------------------------------------------------------------------------
# Compiled patterns — defined once at module level for performance
# ---------------------------------------------------------------------------

_RE_TIME = re.compile(
    r'<span\s[^>]*class="text-\[14px\]\s+SFProDisplayBold\s+ml-2"[^>]*>\s*'
    r'(\d{2}:\d{2}:\d{2})'
    r'\s*</span>',
)

_RE_DATE = re.compile(
    r'<span\s[^>]*class="text-\[14px\]\s+text-\[#FF0000\]\s+SFProDisplayBold\s+ml-2"[^>]*>\s*'
    r'(\d{4}-\d{2}-\d{2})'
    r'\s*</span>',
)

# Description: the bare <div> that follows the time/date wrapper </div>
# We look for </div>\n...whitespace...<div>\n...content...\n...</div>
# Use DOTALL + non-greedy so we grab the FIRST such block.
_RE_DESC = re.compile(
    r'</div>\s*<div>\s*(.*?)\s*</div>',
    re.DOTALL,
)

_RE_FONT_OPEN  = re.compile(r'<font[^>]*>')
_RE_FONT_CLOSE = re.compile(r'</font>')
_RE_KAKKO      = re.compile(r'【([^】]*)】')
_RE_WHITESPACE = re.compile(r'\s+')


def _clean_description(raw: str) -> str:
    """Strip HTML tags and normalise whitespace from a description string."""
    text = _RE_FONT_OPEN.sub('', raw)
    text = _RE_FONT_CLOSE.sub('', text)
    text = _RE_KAKKO.sub(r' \1 ', text)   # 【X】 → ' X ' (preserve spacing)
    text = _RE_WHITESPACE.sub(' ', text).strip()
    return text


def parse_tracking_events(html: str) -> list[JTEventRaw]:
    """
    Parse tracking events from JT Express HTML response.

    Returns events in chronological order (oldest first).
    Raises ValueError if no events could be parsed.
    """
    events: list[JTEventRaw] = []

    # Each event block starts with this marker.  Split on it and process
    # each chunk individually.
    marker = '<div class="result-vandon-item flex flex-col'
    parts = html.split(marker)

    for part in parts[1:]:
        chunk = marker + part

        # --- time ---
        time_m = _RE_TIME.search(chunk)
        if not time_m:
            continue

        # --- date ---
        date_m = _RE_DATE.search(chunk)
        if not date_m:
            continue

        # --- description ---
        # The description <div> comes after the closing </div> of the
        # time/date block.  Find the position just past the date span's
        # closing tag and search from there.
        search_from = date_m.end()
        desc_m = _RE_DESC.search(chunk, search_from)
        if not desc_m:
            continue

        description = _clean_description(desc_m.group(1))
        if not description:
            continue

        events.append(JTEventRaw(
            time_str=time_m.group(1),
            date_str=date_m.group(1),
            description=description,
        ))

    if not events:
        if 'result_vandon' in html and 'result-vandon-item' not in html:
            raise ValueError("No tracking events found for this order")
        if 'không tìm thấy' in html.lower() or 'vận đơn không tồn tại' in html.lower():
            raise ValueError("Tracking code not found")
        raise ValueError("Could not parse tracking events from HTML")

    # HTML lists newest-first; reverse to get chronological order.
    events.reverse()
    return events


def parse_datetime(date_str: str, time_str: str) -> datetime:
    """
    Parse JT Express date/time strings into a datetime object.

    Args:
        date_str: "YYYY-MM-DD"
        time_str: "HH:MM:SS"

    Returns:
        UTC datetime (Vietnam time is UTC+7, but stored as-is for now).
    """
    dt_local = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
    return dt_local.replace(tzinfo=timezone.utc)


def detect_status_from_description(description: str) -> TrackingStatus:
    """
    Map a Vietnamese event description to a TrackingStatus enum value.
    """
    desc = description.lower()

    if any(p in desc for p in [
        "giao hàng thành công",
        "đã giao thành công",
        "chuyển hoàn thành công",
        "đơn hàng đã giao",
    ]):
        return TrackingStatus.DELIVERED

    if any(p in desc for p in [
        "đang giao hàng",
        "đang giao",
        "nhân viên",
    ]):
        return TrackingStatus.OUT_FOR_DELIVERY

    if any(p in desc for p in [
        "đã lấy hàng",
        "đã thu gom",
    ]):
        return TrackingStatus.PICKED_UP

    if any(p in desc for p in [
        "đã tiếp nhận",
        "tiếp nhận vận đơn",
        "đã tạo đơn",
    ]):
        return TrackingStatus.CREATED

    if any(p in desc for p in [
        "đang chuyển",
        "đã được chuyển đến",
        "hàng đã được chuyển",
    ]):
        return TrackingStatus.IN_TRANSIT

    return TrackingStatus.IN_TRANSIT
