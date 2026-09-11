"""Processing time tracking and auto-footer utilities for Telegram messages."""
from __future__ import annotations

import contextvars
import logging
import re
import time
from typing import Any

from telegram.constants import ParseMode
from telegram.ext import ExtBot

logger = logging.getLogger(__name__)

# Context variables to track update processing lifecycle per async task
current_request_start_time: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "current_request_start_time", default=None
)
current_request_chat_id: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "current_request_chat_id", default=None
)
current_request_lang: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_request_lang", default="vi"
)

# Regex to detect and strip previous timing footers when editing messages
_TIMING_REGEX = re.compile(
    r"(?:\n\n|\n)?(?:<i>)?⏱️\s*(?:(?:Thời gian xử lý|Processing time|処理時間):\s*)?[\d\.]+\s*s(?:</i>)?\s*$",
    re.IGNORECASE,
)

# Localized labels
_LABELS = {
    "vi": "⏱️ Thời gian xử lý: {time}s",
    "en": "⏱️ Processing time: {time}s",
    "ja": "⏱️ 処理時間: {time}s",
}


def set_request_context(chat_id: int | None, lang: str = "vi") -> tuple[Any, Any, Any]:
    """Set the start time, chat id, and user language for the current update task."""
    token_time = current_request_start_time.set(time.perf_counter())
    token_chat = current_request_chat_id.set(chat_id)
    token_lang = current_request_lang.set(lang or "vi")
    return token_time, token_chat, token_lang


def update_request_lang(lang: str) -> None:
    """Update user language for the current request context."""
    if lang:
        current_request_lang.set(lang)


def reset_request_context(tokens: tuple[Any, Any, Any]) -> None:
    """Reset the context variables using the tokens from set_request_context."""
    token_time, token_chat, token_lang = tokens
    current_request_start_time.reset(token_time)
    current_request_chat_id.reset(token_chat)
    current_request_lang.reset(token_lang)


def strip_timing_footer(text: str) -> str:
    """Strip any existing timing footer from text."""
    return _TIMING_REGEX.sub("", text).rstrip()


def format_timing_footer(elapsed: float, lang: str = "vi", parse_mode: str | None = None) -> str:
    """Format the localized processing time footer based on elapsed seconds and parse mode."""
    time_str = f"{max(0.01, elapsed):.2f}"
    template = _LABELS.get(lang, _LABELS["vi"])
    raw = template.format(time=time_str)

    mode_str = str(parse_mode or "").upper()
    if mode_str in ("HTML", str(ParseMode.HTML).upper()):
        return f"\n\n<i>{raw}</i>"
    elif "MARKDOWN" in mode_str:
        return f"\n\n_{raw}_"
    return f"\n\n{raw}"


def append_processing_time(
    text: str,
    chat_id: int | str | None = None,
    parse_mode: str | None = None,
) -> str:
    """Append processing time footer to text if in an active request context."""
    start_time = current_request_start_time.get()
    if start_time is None or not isinstance(text, str) or not text.strip():
        return text

    req_chat_id = current_request_chat_id.get()
    # If this message is addressed to a different chat (e.g. admin broadcast), do not append timing
    if req_chat_id is not None and chat_id is not None and str(chat_id) != str(req_chat_id):
        return text

    # Skip temporary loading/in-progress indicators
    if "⏳" in text:
        return text

    elapsed = time.perf_counter() - start_time
    lang = current_request_lang.get() or "vi"
    footer = format_timing_footer(elapsed, lang=lang, parse_mode=parse_mode)
    cleaned_text = strip_timing_footer(text)

    # Respect Telegram max message length (4096)
    max_len = 4096
    if len(cleaned_text) + len(footer) > max_len:
        cleaned_text = cleaned_text[: max_len - len(footer)]

    return cleaned_text + footer


class TimedBot(ExtBot):
    """Custom ExtBot subclass that automatically appends processing time to outgoing messages."""

    async def send_message(self, *args: Any, **kwargs: Any) -> Any:
        try:
            text = kwargs.get("text") if "text" in kwargs else (args[1] if len(args) > 1 else None)
            chat_id = kwargs.get("chat_id") if "chat_id" in kwargs else (args[0] if len(args) > 0 else None)
            parse_mode = kwargs.get("parse_mode") if "parse_mode" in kwargs else (args[2] if len(args) > 2 else None)

            if isinstance(text, str):
                new_text = append_processing_time(text, chat_id=chat_id, parse_mode=parse_mode)
                if new_text != text:
                    if "text" in kwargs:
                        kwargs = dict(kwargs)
                        kwargs["text"] = new_text
                    elif len(args) > 1:
                        args = (args[0], new_text, *args[2:])
        except Exception:
            logger.debug("Failed to append processing time in send_message", exc_info=True)

        return await super().send_message(*args, **kwargs)

    async def edit_message_text(self, *args: Any, **kwargs: Any) -> Any:
        try:
            text = kwargs.get("text") if "text" in kwargs else (args[0] if len(args) > 0 else None)
            chat_id = kwargs.get("chat_id") if "chat_id" in kwargs else (args[1] if len(args) > 1 else None)
            parse_mode = kwargs.get("parse_mode") if "parse_mode" in kwargs else (args[5] if len(args) > 5 else None)

            if isinstance(text, str):
                new_text = append_processing_time(text, chat_id=chat_id, parse_mode=parse_mode)
                if new_text != text:
                    if "text" in kwargs:
                        kwargs = dict(kwargs)
                        kwargs["text"] = new_text
                    elif len(args) > 0:
                        args = (new_text, *args[1:])
        except Exception:
            logger.debug("Failed to append processing time in edit_message_text", exc_info=True)

        return await super().edit_message_text(*args, **kwargs)

