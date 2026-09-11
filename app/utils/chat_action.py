"""Decorators for displaying Telegram chat actions while handlers run."""
from __future__ import annotations

import logging
from functools import wraps
from typing import Awaitable, Callable, TypeVar

from telegram import Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
from telegram.ext import CallbackContext

from app.utils.timing import reset_request_context, set_request_context

logger = logging.getLogger(__name__)

HandlerResult = TypeVar("HandlerResult")
HandlerCallback = Callable[[Update, CallbackContext], Awaitable[HandlerResult]]


def with_typing_action(handler: HandlerCallback[HandlerResult]) -> HandlerCallback[HandlerResult]:
    """Send a typing indicator and track processing time for user-facing bot actions."""

    @wraps(handler)
    async def wrapped(update: Update, context: CallbackContext) -> HandlerResult:
        chat = update.effective_chat
        lang = "vi"
        if context and context.user_data:
            lang = context.user_data.get("language", "vi")

        tokens = set_request_context(chat.id if chat else None, lang=lang)
        try:
            if chat is not None:
                try:
                    await context.bot.send_chat_action(
                        chat_id=chat.id,
                        action=ChatAction.TYPING,
                    )
                except TelegramError:
                    # A failed indicator must never prevent the actual action.
                    logger.debug(
                        "Could not send typing action to chat %s",
                        chat.id,
                        exc_info=True,
                    )

            return await handler(update, context)
        finally:
            reset_request_context(tokens)

    return wrapped

