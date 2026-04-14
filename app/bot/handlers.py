import logging
from datetime import datetime, timezone
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler

from app.core.i18n import I18n
from tracking.service import TrackingService
from tracking.types import TrackingStatus

logger = logging.getLogger(__name__)

WAITING_FOR_TRACKING_CODE = 1
ITEMS_PER_PAGE = 10


class TrackingHandlers:
    def __init__(self, i18n: I18n, tracking_service: TrackingService) -> None:
        self._i18n = i18n
        self._service = tracking_service

    def _get_user_lang(self, context: CallbackContext) -> str:
        return context.user_data.get("language", "vi")

    def _set_user_lang(self, context: CallbackContext, lang: str) -> None:
        context.user_data["language"] = lang

    @staticmethod
    def _esc(value: object) -> str:
        return escape(str(value))

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
            await update.callback_query.edit_message_text(
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

    async def _show_main_menu(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        await self._send_or_edit(
            update=update,
            context=context,
            chat_id=chat_id,
            text=f"✨ <b>{self._esc(self._i18n.t('help_intro', lang))}</b>",
            reply_markup=self._build_main_keyboard(lang),
            parse_mode="HTML",
        )

    async def start_command(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.effective_chat.id
        context.user_data.setdefault("language", "vi")

        lang = self._get_user_lang(context)
        await update.message.reply_text(
            f"✨ <b>{self._esc(self._i18n.t('help_intro', lang))}</b>",
            reply_markup=self._build_main_keyboard(lang),
            parse_mode="HTML",
        )

    async def help_command(self, update: Update, context: CallbackContext) -> None:
        lang = self._get_user_lang(context)
        await self._send_help_intro(
            update.effective_chat.id,
            update,
            context,
            lang,
            edit_message=False,
        )

    async def _send_help_intro(self, chat_id: int, update: Update, context: CallbackContext, lang: str, edit_message: bool = False) -> None:
        text = f"✨ <b>{self._esc(self._i18n.t('help_intro', lang))}</b>"
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
            await update.callback_query.edit_message_text(
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
        text = f"👤 <b>{self._esc(self._i18n.t('help_profile', lang))}</b>\n\n"
        text += f"🆔 <b>Chat ID:</b> <code>{chat_id}</code>\n"
        text += f"🌐 <b>Language:</b> <i>{self._esc(self._i18n.language_name(lang, lang))}</i>"

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="help:intro")],
            ]
        )

        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")

    async def _send_help_command(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        text = f"📚 <b>{self._esc(self._i18n.t('help_command', lang))}</b>\n\n"
        text += "• <code>/start</code> - Main menu\n"
        text += "• <code>/list</code> - List orders\n"
        text += "• <code>/add</code> - Add tracking code\n"
        text += "• <code>/remove</code> - Remove tracking code\n"
        text += "• <code>/help</code> - Show help\n"
        text += "• <code>/lang</code> - Change language"

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="help:intro")],
            ]
        )

        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")

    async def _send_help_language(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        text = f"🌐 <b>{self._esc(self._i18n.t('help_language', lang))}</b>\n\n"
        text += "<i>Available languages:</i>\n"
        for lang_code in self._i18n.supported_languages():
            text += f"• {self._esc(self._i18n.language_name(lang_code, lang))}\n"

        buttons = []
        for lang_code in self._i18n.supported_languages():
            buttons.append(
                InlineKeyboardButton(
                    self._i18n.language_name(lang_code, lang),
                    callback_data=f"lang:set:{lang_code}",
                )
            )

        keyboard = InlineKeyboardMarkup(
            [buttons, [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="help:intro")]]
        )

        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")

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

    async def lang_callback(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id
        data = query.data

        if data == "lang:list":
            lang = self._get_user_lang(context)
            text = f"🌐 <b>{self._esc(self._i18n.t('help_language', lang))}</b>\n\n"
            text += "<i>Available languages:</i>"

            buttons = []
            for lang_code in self._i18n.supported_languages():
                buttons.append(
                    InlineKeyboardButton(
                        self._i18n.language_name(lang_code, lang),
                        callback_data=f"lang:set:{lang_code}",
                    )
                )

            keyboard = InlineKeyboardMarkup(
                [buttons, [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:menu")]]
            )

            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        elif data.startswith("lang:set:"):
            new_lang = data.split(":")[-1]
            self._set_user_lang(context, new_lang)
            text = f"✅ <b>{self._esc(self._i18n.t('lang_changed', new_lang))}</b>"
            await query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("OK", callback_data="cmd:menu")]]
                ),
                parse_mode="HTML",
            )

    async def cmd_callback(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)
        data = query.data

        if data == "cmd:list":
            context.user_data.pop("add_waiting_carrier", None)
            context.user_data.pop("add_waiting_chat_id", None)
            await self._show_order_list(chat_id, update, context, lang)
        elif data == "cmd:add":
            await self._show_add_carrier_selection(chat_id, update, context, lang)
        elif data == "cmd:menu":
            context.user_data.pop("add_waiting_carrier", None)
            context.user_data.pop("add_waiting_chat_id", None)
            await self._show_main_menu(chat_id, update, context, lang)

    async def _show_order_list(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        trackings = self._service.list_trackings(chat_id)

        if not trackings:
            text = f"📭 <b>{self._esc(self._i18n.t('list_empty', lang))}</b>"
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:menu")]]
            )
            await self._send_or_edit(update, context, chat_id, text, keyboard, parse_mode="HTML")
            return

        text = f"📦 <b>{self._esc(self._i18n.t('list_header', lang))}</b>\n\n"
        text += "<i>Tap an order below to view details.</i>"
        buttons = []
        for tracking in trackings:
            status_text = self._i18n.status(tracking.last_status, lang)
            display_text = f"📌 {tracking.tracking_code} • {status_text}"
            buttons.append(
                [InlineKeyboardButton(display_text, callback_data=f"order:{tracking.id}")]
            )

        buttons.append([InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:menu")])
        keyboard = InlineKeyboardMarkup(buttons)

        await self._send_or_edit(update, context, chat_id, text, keyboard, parse_mode="HTML")

    async def order_callback(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)
        data = query.data
        tracking_id = int(data.split(":")[-1])

        tracking = self._service.get_tracking_detail(chat_id, tracking_id)
        if tracking is None:
            await query.answer("Order not found", show_alert=True)
            return

        text = "📦 <b>Order Detail</b>\n\n"
        text += f"🔢 <b>Code:</b> <code>{self._esc(tracking.tracking_code)}</code>\n"
        text += f"🚚 <b>Carrier:</b> {self._esc(tracking.carrier.name)}\n"
        text += f"📊 <b>Status:</b> <b>{self._esc(self._i18n.status(tracking.last_status, lang))}</b>\n"

        events = self._service.get_tracking_events(chat_id, tracking_id)
        if events:
            latest = events[-1]
            if latest.location:
                text += f"📍 <b>Location:</b> <i>{self._esc(latest.location[:60])}</i>\n"
            if latest.event_time:
                formatted_time = latest.event_time.strftime("%d/%m/%Y %H:%M") if isinstance(latest.event_time, datetime) else str(latest.event_time)
                text += f"🕒 <b>Updated:</b> <code>{self._esc(formatted_time)}</code>"

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        self._i18n.t("btn_timeline", lang),
                        callback_data=f"order_timeline:{tracking_id}:0",
                    ),
                    InlineKeyboardButton(
                        self._i18n.t("btn_remove", lang),
                        callback_data=f"remove:{tracking_id}",
                    ),
                ],
                [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:list")],
            ]
        )

        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")

    async def order_timeline_callback(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)
        parts = query.data.split(":")
        tracking_id = int(parts[1])
        page = int(parts[2])

        tracking = self._service.get_tracking_detail(chat_id, tracking_id)
        if tracking is None:
            await query.answer("Order not found", show_alert=True)
            return

        events = self._service.get_tracking_events(chat_id, tracking_id)
        total_pages = (len(events) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        if total_pages == 0:
            total_pages = 1

        if page < 0:
            page = 0
        if page >= total_pages:
            page = total_pages - 1

        start_idx = page * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        page_events = events[start_idx:end_idx]

        text = (
            f"📅 <b>{self._esc(self._i18n.t('help_timeline_title', lang))}</b>\n"
            f"🔢 <code>{self._esc(tracking.tracking_code)}</code>\n"
            f"🚚 {self._esc(tracking.carrier.name)}\n\n"
        )

        if not page_events:
            text += "<i>No timeline events yet.</i>\n\n"

        for i, event in enumerate(page_events):
            event_num = start_idx + i + 1
            formatted_time = event.event_time.strftime("%d/%m %H:%M") if isinstance(event.event_time, datetime) else str(event.event_time)
            status_text = self._i18n.status(event.status, lang)
            text += f"<b>{event_num}.</b> <code>{self._esc(formatted_time)}</code> • <b>{self._esc(status_text)}</b>\n"
            if event.location:
                text += f"📍 <i>{self._esc(event.location[:60])}</i>\n"
            if event.description:
                text += f"↳ {self._esc(event.description[:90])}\n"
            text += "\n"

        buttons = []
        nav_buttons = [
            InlineKeyboardButton(
                self._i18n.t("btn_prev", lang),
                callback_data=f"order_timeline:{tracking_id}:{page - 1}" if page > 0 else "noop",
            ),
            InlineKeyboardButton(
                self._i18n.t("pagination", lang, page=page + 1, total=total_pages),
                callback_data="noop",
            ),
            InlineKeyboardButton(
                self._i18n.t("btn_next", lang),
                callback_data=f"order_timeline:{tracking_id}:{page + 1}" if page < total_pages - 1 else "noop",
            ),
        ]

        buttons.append(nav_buttons)
        buttons.append(
            [
                InlineKeyboardButton(
                    self._i18n.t("btn_back", lang),
                    callback_data=f"order:{tracking_id}",
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(buttons)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")

    async def _show_add_carrier_selection(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        text = f"🚚 <b>{self._esc(self._i18n.t('add_select_carrier', lang))}</b>"

        buttons = []
        for carrier_code, carrier_name in [("jtexpress", "JT Express"), ("shopeeexpress", "Shopee Express")]:
            buttons.append([InlineKeyboardButton(carrier_name, callback_data=f"add_carrier:{carrier_code}")])
        buttons.append([InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:menu")])

        keyboard = InlineKeyboardMarkup(buttons)
        await self._send_or_edit(update, context, chat_id, text, keyboard, parse_mode="HTML")

    async def add_carrier_callback(self, update: Update, context: CallbackContext) -> int:
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)
        carrier = query.data.split(":")[-1]

        context.user_data["add_waiting_carrier"] = carrier
        context.user_data["add_waiting_chat_id"] = chat_id

        text = self._i18n.t("add_enter_code", lang)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:add")]]
        )

        await query.edit_message_text(
            f"✍️ <b>{self._esc(text)}</b>\n\n<i>Example:</i> <code>SPXVN123456789</code>",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        return WAITING_FOR_TRACKING_CODE

    async def add_tracking_message(self, update: Update, context: CallbackContext) -> int:
        if context.user_data.get("add_waiting_carrier") is None:
            return ConversationHandler.END

        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)
        tracking_code = update.message.text.strip()
        carrier = context.user_data.get("add_waiting_carrier")

        try:
            tracking = self._service.add_tracking(chat_id, tracking_code, carrier)
            status_text = self._i18n.status(tracking.last_status, lang)
            raw_text = self._i18n.t(
                "add_success",
                lang,
                code=tracking.tracking_code,
                carrier=tracking.carrier.name,
                status=status_text,
            )
            text = f"✅ <b>{self._esc(raw_text)}</b>"
        except ValueError as e:
            error_key = str(e)
            msg = self._i18n.t(error_key, lang) if self._i18n.has_key(error_key, lang) else "Error adding tracking"
            text = f"❌ <b>{self._esc(msg)}</b>"

        context.user_data.pop("add_waiting_carrier", None)
        context.user_data.pop("add_waiting_chat_id", None)

        try:
            await update.message.delete()
        except Exception:
            pass
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=self._build_main_keyboard(lang),
            parse_mode="HTML",
        )

        return ConversationHandler.END

    async def remove_callback(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)
        tracking_id = int(query.data.split(":")[-1])

        tracking = self._service.get_tracking_detail(chat_id, tracking_id)
        if tracking is None:
            await query.answer("Order not found", show_alert=True)
            return

        self._service.remove_tracking(chat_id, tracking.tracking_code)

        text = f"🗑️ <b>{self._esc(self._i18n.t('remove_success', lang, code=tracking.tracking_code))}</b>"
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:list")]]
        )

        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")

    async def add_command(self, update: Update, context: CallbackContext) -> int:
        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)

        try:
            await update.message.delete()
        except Exception:
            pass
        await self._show_add_carrier_selection(chat_id, update, context, lang)

        return WAITING_FOR_TRACKING_CODE

    async def list_command(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)

        try:
            await update.message.delete()
        except Exception:
            pass
        await self._show_order_list(chat_id, update, context, lang)

    async def remove_command(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)

        trackings = self._service.list_trackings(chat_id)

        if not trackings:
            text = f"📭 <b>{self._esc(self._i18n.t('list_empty', lang))}</b>"
            await update.message.reply_text(text, parse_mode="HTML")
            return

        buttons = []
        for tracking in trackings:
            buttons.append(
                [
                    InlineKeyboardButton(
                        tracking.tracking_code,
                        callback_data=f"remove:{tracking.id}",
                    )
                ]
            )

        keyboard = InlineKeyboardMarkup(buttons)
        await update.message.delete()
        await context.bot.send_message(
            chat_id=chat_id,
            text="🗑️ <b>Select order to remove:</b>",
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    async def lang_command(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)

        buttons = []
        for lang_code in self._i18n.supported_languages():
            buttons.append(
                InlineKeyboardButton(
                    self._i18n.language_name(lang_code, lang),
                    callback_data=f"lang:set:{lang_code}",
                )
            )

        keyboard = InlineKeyboardMarkup([buttons])

        await update.message.reply_text(
            f"🌐 <b>{self._esc(self._i18n.t('help_language', lang))}</b>",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
