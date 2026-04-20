"""UI formatting utilities for Telegram bot messages."""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape

from app.constants.icons import DEFAULT_STATUS_ICON, DISPLAY_TIMEZONE, STATUS_ICONS


def esc(value: object) -> str:
    """Escape HTML special characters."""
    return escape(str(value))


def format_datetime_local(value: datetime, fmt: str) -> str:
    """Format datetime to local timezone."""
    dt = value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(DISPLAY_TIMEZONE).strftime(fmt)


def format_labeled_item(text: str, *, as_code: bool = False, as_italic: bool = False) -> str:
    """Format a label:value pair with HTML tags."""
    if ":" not in text:
        return esc(text)

    label, value = text.split(":", 1)
    escaped_label = esc(label.strip())
    escaped_value = esc(value.strip())

    if as_code:
        rendered_value = f"<code>{escaped_value}</code>"
    elif as_italic:
        rendered_value = f"<i>{escaped_value}</i>"
    else:
        rendered_value = escaped_value

    return f"<b>{escaped_label}:</b> {rendered_value}"


def status_icon(status_code: str) -> str:
    """Get emoji icon for status code."""
    return STATUS_ICONS.get(status_code, DEFAULT_STATUS_ICON)


def split_tracking_code_for_buttons(tracking_code: str) -> tuple[str, str, str]:
    """Split tracking code into 3 balanced parts for button display."""
    code = (tracking_code or "").strip()
    if not code:
        return ("-", "-", "-")

    base = len(code) // 3
    remainder = len(code) % 3
    sizes = [base, base, base]
    for i in range(remainder):
        sizes[i] += 1

    chunks: list[str] = []
    cursor = 0
    for size in sizes:
        if size <= 0:
            chunks.append("-")
            continue
        chunks.append(code[cursor:cursor + size])
        cursor += size

    while len(chunks) < 3:
        chunks.append("-")

    return chunks[0], chunks[1], chunks[2]
