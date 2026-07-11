"""Base handler with shared utilities."""
from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext

from app.i18n import I18n
from app.services.tracking import TrackingService

logger = logging.getLogger(__name__)


class BaseHandler:
    """Base handler with shared utilities for all handlers."""

    def __init__(self, i18n: I18n, tracking_service: TrackingService) -> None:
        self._i18n = i18n
        self._service = tracking_service

    def _get_user_lang(self, context: CallbackContext) -> str:
        return context.user_data.get("language", "vi")

    def _set_user_lang(self, context: CallbackContext, lang: str) -> None:
        context.user_data["language"] = lang

    @staticmethod
    async def _delete_message_quietly(message) -> None:
        try:
            await message.delete()
        except Exception:
            pass

    async def _safe_edit_message_text(
        self,
        query,
        text: str,
        reply_markup: InlineKeyboardMarkup,
        parse_mode: str | None = None,
    ) -> None:
        try:
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        except BadRequest as exc:
            if "message is not modified" in str(exc).lower():
                logger.debug("Skip edit_message_text because content is unchanged")
                return
            raise

    def _build_main_keyboard(self, lang: str) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        self._i18n.t("btn_list", lang),
                        callback_data="cmd:list",
                    ),
                    InlineKeyboardButton(
                        self._i18n.t("btn_add", lang),
                        callback_data="cmd:add",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        self._i18n.t("btn_help", lang),
                        callback_data="help:intro",
                    ),
                    InlineKeyboardButton(
                        self._i18n.t("btn_language", lang),
                        callback_data="lang:list",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        self._i18n.t("btn_mission", lang),
                        callback_data="info:mission",
                    ),
                ],
            ]
        )

    async def _send_or_edit(
        self,
        update: Update,
        context: CallbackContext,
        chat_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup,
        parse_mode: str | None = None,
    ) -> None:
        if update.callback_query:
            await self._safe_edit_message_text(
                update.callback_query,
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
