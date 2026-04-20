"""Language selection handlers."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from app.handlers.base_handler import BaseHandler
from app.utils import formatter


class LanguageHandler(BaseHandler):
    """Handler for language selection."""

    async def lang_command(self, update: Update, context: CallbackContext) -> None:
        lang = self._get_user_lang(context)
        keyboard = InlineKeyboardMarkup([self._build_language_buttons(lang)])

        await update.message.reply_text(
            f"<b>{formatter.esc(self._i18n.t('help_language', lang))}</b>",
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    async def lang_callback(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id
        data = query.data

        if data == "lang:list":
            lang = self._get_user_lang(context)
            text = f"<b>{formatter.esc(self._i18n.t('help_language', lang))}</b>\n\n"
            text += f"<i>{formatter.esc(self._i18n.t('available_languages', lang))}</i>"

            keyboard = InlineKeyboardMarkup(
                [
                    self._build_language_buttons(lang),
                    [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:menu")],
                ]
            )

            await self._safe_edit_message_text(query, text, reply_markup=keyboard, parse_mode="HTML")
        elif data.startswith("lang:set:"):
            new_lang = data.split(":")[-1]
            self._set_user_lang(context, new_lang)
            text = f"<b>{formatter.esc(self._i18n.t('lang_changed', new_lang))}</b>"
            await self._safe_edit_message_text(
                query,
                text,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("OK", callback_data="cmd:menu")]]
                ),
                parse_mode="HTML",
            )

    def _build_language_buttons(self, lang: str) -> list[InlineKeyboardButton]:
        return [
            InlineKeyboardButton(
                self._i18n.language_name(lang_code, lang),
                callback_data=f"lang:set:{lang_code}",
            )
            for lang_code in self._i18n.supported_languages()
        ]
