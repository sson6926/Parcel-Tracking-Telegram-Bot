"""Help and profile handlers."""
from __future__ import annotations

from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from app.handlers.base_handler import BaseHandler
from app.utils import formatter


class HelpHandler(BaseHandler):
    """Handler for help and profile commands."""

    async def help_command(self, update: Update, context: CallbackContext) -> None:
        lang = self._get_user_lang(context)
        await self._send_help_intro(
            update.effective_chat.id,
            update,
            context,
            lang,
            edit_message=False,
        )

    async def help_callback(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)
        data = query.data

        if data == "help:intro":
            await self._send_help_intro(chat_id, update, context, lang, edit_message=True)
        elif data == "help:profile":
            await self._send_help_profile(chat_id, update, context, lang)
        elif data == "help:command":
            await self._send_help_command(chat_id, update, context, lang)
        elif data == "help:language":
            await self._send_help_language(chat_id, update, context, lang)

    async def _send_help_intro(self, chat_id: int, update: Update, context: CallbackContext, lang: str, edit_message: bool = False) -> None:
        text = f"<b>{formatter.esc(self._i18n.t('help_intro', lang))}</b>"
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        self._i18n.t("help_profile", lang),
                        callback_data="help:profile",
                    ),
                    InlineKeyboardButton(
                        self._i18n.t("help_command", lang),
                        callback_data="help:command",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        self._i18n.t("help_language", lang),
                        callback_data="help:language",
                    ),
                ],
            ]
        )

        if edit_message and update.callback_query:
            await self._safe_edit_message_text(
                update.callback_query,
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

    async def _send_help_profile(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        summary = self._service.get_user_profile_summary(chat_id)
        joined_at = summary.get("joined_at")
        if isinstance(joined_at, datetime):
            joined_value = formatter.format_datetime_local(joined_at, "%d/%m/%Y %H:%M")
        else:
            joined_value = self._i18n.t("profile_not_available", lang)

        text = f"<b>{formatter.esc(self._i18n.t('help_profile', lang))}</b>\n\n"
        text += f"<b>{formatter.esc(self._i18n.t('label_chat_id', lang))}:</b> <code>{chat_id}</code>\n"
        text += f"<b>{formatter.esc(self._i18n.t('label_language', lang))}:</b> <i>{formatter.esc(self._i18n.language_name(lang, lang))}</i>"
        text += "\n\n"
        text += f"<b>{formatter.esc(self._i18n.t('profile_stats_title', lang))}</b>\n"
        text += f"• {formatter.esc(self._i18n.t('profile_joined_at', lang, value=joined_value))}\n"
        text += f"• {formatter.esc(self._i18n.t('profile_total_orders', lang, value=summary.get('total_orders', 0)))}\n"
        text += f"• {formatter.esc(self._i18n.t('profile_active_orders', lang, value=summary.get('active_orders', 0)))}\n"
        text += f"• {formatter.esc(self._i18n.t('profile_delivered_orders', lang, value=summary.get('delivered_orders', 0)))}\n"
        text += f"• {formatter.esc(self._i18n.t('profile_failed_orders', lang, value=summary.get('failed_orders', 0)))}\n"
        text += f"• {formatter.esc(self._i18n.t('profile_carriers_used', lang, value=summary.get('carriers_used', 0)))}"

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="help:intro")],
            ]
        )

        await self._safe_edit_message_text(update.callback_query, text, reply_markup=keyboard, parse_mode="HTML")

    async def _send_help_command(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        text = f"<b>{formatter.esc(self._i18n.t('help_command', lang))}</b>\n\n"
        text += f"🏠 <code>/start</code> - {formatter.esc(self._i18n.t('cmd_desc_start', lang))}\n"
        text += f"📋 <code>/list</code> - {formatter.esc(self._i18n.t('cmd_desc_list', lang))}\n"
        text += f"➕ <code>/add</code> - {formatter.esc(self._i18n.t('cmd_desc_add', lang))}\n"
        text += f"🗑️ <code>/remove</code> - {formatter.esc(self._i18n.t('cmd_desc_remove', lang))}\n"
        text += f"ℹ️ <code>/help</code> - {formatter.esc(self._i18n.t('cmd_desc_help', lang))}\n"
        text += f"🌐 <code>/lang</code> - {formatter.esc(self._i18n.t('cmd_desc_lang', lang))}"

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="help:intro")],
            ]
        )

        await self._safe_edit_message_text(update.callback_query, text, reply_markup=keyboard, parse_mode="HTML")

    async def _send_help_language(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        text = f"<b>{formatter.esc(self._i18n.t('help_language', lang))}</b>\n\n"
        text += f"<i>{formatter.esc(self._i18n.t('available_languages', lang))}</i>\n"
        for lang_code in self._i18n.supported_languages():
            text += f"🌍 {formatter.esc(self._i18n.language_name(lang_code, lang))}\n"

        keyboard = InlineKeyboardMarkup(
            [
                self._build_language_buttons(lang),
                [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="help:intro")],
            ]
        )

        await self._safe_edit_message_text(update.callback_query, text, reply_markup=keyboard, parse_mode="HTML")

    def _build_language_buttons(self, lang: str) -> list[InlineKeyboardButton]:
        return [
            InlineKeyboardButton(
                self._i18n.language_name(lang_code, lang),
                callback_data=f"lang:set:{lang_code}",
            )
            for lang_code in self._i18n.supported_languages()
        ]
