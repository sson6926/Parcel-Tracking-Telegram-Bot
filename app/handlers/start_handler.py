"""Start command handler."""
from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackContext

from app.handlers.base_handler import BaseHandler
from app.utils import formatter


class StartHandler(BaseHandler):
    """Handler for /start command."""

    async def start_command(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.effective_chat.id
        telegram_user = update.effective_user
        self._service.ensure_user(
            chat_id,
            telegram_username=telegram_user.username if telegram_user else None,
            display_name=telegram_user.full_name if telegram_user else None,
        )
        context.user_data.setdefault("language", "vi")

        lang = self._get_user_lang(context)
        await update.message.reply_text(
            f"<b>{formatter.esc(self._i18n.t('help_intro', lang))}</b>",
            reply_markup=self._build_main_keyboard(lang),
            parse_mode="HTML",
        )

    async def show_main_menu(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        await self._send_or_edit(
            update=update,
            context=context,
            chat_id=chat_id,
            text=f"<b>{formatter.esc(self._i18n.t('help_intro', lang))}</b>",
            reply_markup=self._build_main_keyboard(lang),
            parse_mode="HTML",
        )
