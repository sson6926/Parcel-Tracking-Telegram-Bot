from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext, ConversationHandler

from app.core.i18n import I18n
from tracking.service import TrackingService
from tracking.types import TrackingStatus

logger = logging.getLogger(__name__)

WAITING_FOR_TRACKING_CODE = 1
ITEMS_PER_PAGE = 10


class TrackingHandlers:
    _STATUS_ICONS = {
        "CREATED": "🆕",
        "PICKED_UP": "📥",
        "IN_TRANSIT": "🚚",
        "OUT_FOR_DELIVERY": "🛵",
        "DELIVERED": "✅",
        "FAILED": "❌",
    }
    _DISPLAY_TIMEZONE = timezone(timedelta(hours=7))

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

    def _format_datetime_local(self, value: datetime, fmt: str) -> str:
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(self._DISPLAY_TIMEZONE).strftime(fmt)

    def _format_labeled_item(self, text: str, *, as_code: bool = False, as_italic: bool = False) -> str:
        if ":" not in text:
            return self._esc(text)

        label, value = text.split(":", 1)
        escaped_label = self._esc(label.strip())
        escaped_value = self._esc(value.strip())

        if as_code:
            rendered_value = f"<code>{escaped_value}</code>"
        elif as_italic:
            rendered_value = f"<i>{escaped_value}</i>"
        else:
            rendered_value = escaped_value

        return f"<b>{escaped_label}:</b> {rendered_value}"

    def _status_icon(self, status_code: str) -> str:
        return self._STATUS_ICONS.get(status_code, "📦")

    @staticmethod
    def _split_tracking_code_for_buttons(tracking_code: str) -> tuple[str, str, str]:
        code = (tracking_code or "").strip()
        if not code:
            return ("-", "-", "-")

        # Keep 3 middle cells balanced so the row visually matches 1/5 - 3/5 - 1/5.
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

    async def _show_main_menu(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        await self._send_or_edit(
            update=update,
            context=context,
            chat_id=chat_id,
            text=f"<b>{self._esc(self._i18n.t('help_intro', lang))}</b>",
            reply_markup=self._build_main_keyboard(lang),
            parse_mode="HTML",
        )

    async def start_command(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.effective_chat.id
        context.user_data.setdefault("language", "vi")

        lang = self._get_user_lang(context)
        await update.message.reply_text(
            f"<b>{self._esc(self._i18n.t('help_intro', lang))}</b>",
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
        text = f"<b>{self._esc(self._i18n.t('help_intro', lang))}</b>"
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
            joined_value = self._format_datetime_local(joined_at, "%d/%m/%Y %H:%M")
        else:
            joined_value = self._i18n.t("profile_not_available", lang)

        text = f"<b>{self._esc(self._i18n.t('help_profile', lang))}</b>\n\n"
        text += f"<b>{self._esc(self._i18n.t('label_chat_id', lang))}:</b> <code>{chat_id}</code>\n"
        text += f"<b>{self._esc(self._i18n.t('label_language', lang))}:</b> <i>{self._esc(self._i18n.language_name(lang, lang))}</i>"
        text += "\n\n"
        text += f"<b>{self._esc(self._i18n.t('profile_stats_title', lang))}</b>\n"
        text += f"• {self._esc(self._i18n.t('profile_joined_at', lang, value=joined_value))}\n"
        text += f"• {self._esc(self._i18n.t('profile_total_orders', lang, value=summary.get('total_orders', 0)))}\n"
        text += f"• {self._esc(self._i18n.t('profile_active_orders', lang, value=summary.get('active_orders', 0)))}\n"
        text += f"• {self._esc(self._i18n.t('profile_delivered_orders', lang, value=summary.get('delivered_orders', 0)))}\n"
        text += f"• {self._esc(self._i18n.t('profile_failed_orders', lang, value=summary.get('failed_orders', 0)))}\n"
        text += f"• {self._esc(self._i18n.t('profile_carriers_used', lang, value=summary.get('carriers_used', 0)))}"

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="help:intro")],
            ]
        )

        await self._safe_edit_message_text(update.callback_query, text, reply_markup=keyboard, parse_mode="HTML")

    async def _send_help_command(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        text = f"<b>{self._esc(self._i18n.t('help_command', lang))}</b>\n\n"
        text += f"🏠 <code>/start</code> - {self._esc(self._i18n.t('cmd_desc_start', lang))}\n"
        text += f"📋 <code>/list</code> - {self._esc(self._i18n.t('cmd_desc_list', lang))}\n"
        text += f"➕ <code>/add</code> - {self._esc(self._i18n.t('cmd_desc_add', lang))}\n"
        text += f"🗑️ <code>/remove</code> - {self._esc(self._i18n.t('cmd_desc_remove', lang))}\n"
        text += f"ℹ️ <code>/help</code> - {self._esc(self._i18n.t('cmd_desc_help', lang))}\n"
        text += f"🌐 <code>/lang</code> - {self._esc(self._i18n.t('cmd_desc_lang', lang))}"

        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="help:intro")],
            ]
        )

        await self._safe_edit_message_text(update.callback_query, text, reply_markup=keyboard, parse_mode="HTML")

    async def _send_help_language(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        text = f"<b>{self._esc(self._i18n.t('help_language', lang))}</b>\n\n"
        text += f"<i>{self._esc(self._i18n.t('available_languages', lang))}</i>\n"
        for lang_code in self._i18n.supported_languages():
            text += f"🌍 {self._esc(self._i18n.language_name(lang_code, lang))}\n"

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

        await self._safe_edit_message_text(update.callback_query, text, reply_markup=keyboard, parse_mode="HTML")

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
            text = f"<b>{self._esc(self._i18n.t('help_language', lang))}</b>\n\n"
            text += f"<i>{self._esc(self._i18n.t('available_languages', lang))}</i>"

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

            await self._safe_edit_message_text(query, text, reply_markup=keyboard, parse_mode="HTML")
        elif data.startswith("lang:set:"):
            new_lang = data.split(":")[-1]
            self._set_user_lang(context, new_lang)
            text = f"<b>{self._esc(self._i18n.t('lang_changed', new_lang))}</b>"
            await self._safe_edit_message_text(
                query,
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
            text = f"<b>{self._esc(self._i18n.t('list_empty', lang))}</b>"
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:menu")]]
            )
            await self._send_or_edit(update, context, chat_id, text, keyboard, parse_mode="HTML")
            return

        text = f"<b>{self._esc(self._i18n.t('list_header', lang))}</b>\n\n"
        text += f"<i>{self._esc(self._i18n.t('tap_order_hint', lang))}</i>"
        buttons = []
        for tracking in trackings:
            status_icon = self._status_icon(tracking.last_status)
            code_1, code_2, code_3 = self._split_tracking_code_for_buttons(tracking.tracking_code)
            buttons.append(
                [
                    InlineKeyboardButton(status_icon, callback_data=f"order:{tracking.id}"),
                    InlineKeyboardButton(code_1, callback_data=f"order:{tracking.id}"),
                    InlineKeyboardButton(code_2, callback_data=f"order:{tracking.id}"),
                    InlineKeyboardButton(code_3, callback_data=f"order:{tracking.id}"),
                    InlineKeyboardButton("🗑️", callback_data=f"remove:{tracking.id}"),
                ]
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
            await query.answer(self._i18n.t("order_not_found", lang), show_alert=True)
            return

        text = f"<b>{self._esc(self._i18n.t('help_order_detail', lang))}</b>\n\n"
        text += f"🔖 {self._format_labeled_item(self._i18n.t('detail_code', lang, code=tracking.tracking_code), as_code=True)}\n"
        text += f"🚚 {self._format_labeled_item(self._i18n.t('detail_carrier', lang, carrier=tracking.carrier.name))}\n"
        status_icon = self._status_icon(tracking.last_status)
        text += f"{status_icon} {self._format_labeled_item(self._i18n.t('detail_status', lang, status=self._i18n.status(tracking.last_status, lang)))}\n"

        events = self._service.get_tracking_events(chat_id, tracking_id)
        if events:
            latest = events[-1]
            if latest.location:
                text += f"📍 {self._format_labeled_item(self._i18n.t('detail_location', lang, location=latest.location[:60]), as_italic=True)}\n"
            if latest.event_time:
                formatted_time = self._format_datetime_local(latest.event_time, "%d/%m/%Y %H:%M") if isinstance(latest.event_time, datetime) else str(latest.event_time)
                text += f"🕒 {self._format_labeled_item(self._i18n.t('detail_time', lang, time=formatted_time), as_code=True)}"

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

        await self._safe_edit_message_text(query, text, reply_markup=keyboard, parse_mode="HTML")

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
            await query.answer(self._i18n.t("order_not_found", lang), show_alert=True)
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
            f"<b>{self._esc(self._i18n.t('help_timeline_title', lang))}</b>\n"
            f"📦 <code>{self._esc(tracking.tracking_code)}</code>\n"
            f"🚚 {self._esc(tracking.carrier.name)}\n\n"
        )

        if not page_events:
            text += f"<i>{self._esc(self._i18n.t('timeline_empty', lang))}</i>\n\n"

        for i, event in enumerate(page_events):
            event_num = start_idx + i + 1
            formatted_time = self._format_datetime_local(event.event_time, "%d/%m %H:%M") if isinstance(event.event_time, datetime) else str(event.event_time)
            status_text = self._i18n.status(event.status, lang)
            status_icon = self._status_icon(event.status)
            text += f"<b>{event_num}.</b> 🕒 <code>{self._esc(formatted_time)}</code> • {status_icon} <b>{self._esc(status_text)}</b>\n"
            if event.location:
                text += f"📍 <i>{self._esc(event.location[:60])}</i>\n"
            if event.description:
                text += f"↳ {self._esc(event.description[:90])}\n"
            text += "\n"

        buttons = []
        prev_page = total_pages - 1 if page == 0 else page - 1
        next_page = 0 if page == total_pages - 1 else page + 1
        nav_buttons = [
            InlineKeyboardButton(
                self._i18n.t("btn_prev", lang),
                callback_data=f"order_timeline:{tracking_id}:{prev_page}",
            ),
            InlineKeyboardButton(
                f"[{page + 1}/{total_pages}]",
                callback_data="noop",
            ),
            InlineKeyboardButton(
                self._i18n.t("btn_next", lang),
                callback_data=f"order_timeline:{tracking_id}:{next_page}",
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
        await self._safe_edit_message_text(query, text, reply_markup=keyboard, parse_mode="HTML")

    async def _show_add_carrier_selection(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        text = f"<b>{self._esc(self._i18n.t('add_select_carrier', lang))}</b>"

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

        await self._safe_edit_message_text(
            query,
            f"<b>{self._esc(text)}</b>\n\n🔎 <i>{self._esc(self._i18n.t('example_label', lang))}:</i> <code>SPXVN123456789</code>",
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
            text = f"<b>{self._esc(raw_text)}</b>"
        except ValueError as e:
            error_key = str(e)
            msg = self._i18n.t(error_key, lang) if self._i18n.has_key(error_key, lang) else self._i18n.t("error_add_tracking_generic", lang)
            text = f"<b>{self._esc(msg)}</b>"

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

    async def auto_add_shopee_from_message(self, update: Update, context: CallbackContext) -> None:
        if update.message is None:
            return

        # If user is in interactive add flow, keep current behavior unchanged.
        if context.user_data.get("add_waiting_carrier") is not None:
            return

        raw_text = update.message.text or ""
        match = re.match(r"^\s*(SPXVN[0-9A-Z]+)", raw_text, flags=re.IGNORECASE)
        if not match:
            return

        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)
        tracking_code = match.group(1).upper()

        try:
            tracking = self._service.add_tracking(chat_id, tracking_code, "shopeeexpress")
            status_text = self._i18n.status(tracking.last_status, lang)
            raw_success = self._i18n.t(
                "add_success",
                lang,
                code=tracking.tracking_code,
                carrier=tracking.carrier.name,
                status=status_text,
            )
            text = f"<b>{self._esc(raw_success)}</b>"
        except ValueError as e:
            error_key = str(e)
            msg = self._i18n.t(error_key, lang) if self._i18n.has_key(error_key, lang) else self._i18n.t("error_add_tracking_generic", lang)
            text = f"<b>{self._esc(msg)}</b>"

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

    async def remove_callback(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)
        tracking_id = int(query.data.split(":")[-1])

        tracking = self._service.get_tracking_detail(chat_id, tracking_id)
        if tracking is None:
            await query.answer(self._i18n.t("order_not_found", lang), show_alert=True)
            return

        self._service.remove_tracking(chat_id, tracking.tracking_code)
        await query.answer(self._i18n.t("remove_success", lang, code=tracking.tracking_code), show_alert=False)
        await self._show_order_list(chat_id, update, context, lang)

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
            text = f"<b>{self._esc(self._i18n.t('list_empty', lang))}</b>"
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
            text=f"<b>{self._esc(self._i18n.t('remove_select_prompt', lang))}</b>",
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
            f"<b>{self._esc(self._i18n.t('help_language', lang))}</b>",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
