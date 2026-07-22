"""Tracking operations handlers."""
from __future__ import annotations

import logging
import re
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler

from app.constants.icons import TIMELINE_DESCRIPTION_MAX_LEN, TIMELINE_LOCATION_MAX_LEN
from app.constants.user_state import ADD_WAITING_CARRIER, ADD_WAITING_CHAT_ID, ADD_WAITING_JT_PHONE, WAITING_FOR_TRACKING_CODE
from app.handlers.base_handler import BaseHandler
from app.utils import formatter

logger = logging.getLogger(__name__)

ITEMS_PER_PAGE = 10


class TrackingHandler(BaseHandler):
    """Handler for tracking operations (add, list, remove, detail, timeline)."""

    def _clear_add_tracking_context(self, context: CallbackContext) -> None:
        context.user_data.pop(ADD_WAITING_CARRIER, None)
        context.user_data.pop(ADD_WAITING_CHAT_ID, None)
        context.user_data.pop(ADD_WAITING_JT_PHONE, None)

    def _build_add_tracking_result_text(
        self,
        chat_id: int,
        lang: str,
        tracking_code: str,
        carrier_code: str | None,
    ) -> str:
        try:
            tracking = self._service.add_tracking(chat_id, tracking_code, carrier_code)
            status_text = self._i18n.status(tracking.last_status, lang)
            raw_text = self._i18n.t(
                "add_success",
                lang,
                code=tracking.tracking_code,
                carrier=tracking.carrier.name,
                status=status_text,
                credits=self._service.get_user_credits(chat_id),
            )
            return f"<b>{formatter.esc(raw_text)}</b>"
        except ValueError as e:
            error_key = str(e)
            msg = (
                self._i18n.t(error_key, lang)
                if self._i18n.has_key(error_key, lang)
                else self._i18n.t("error_add_tracking_generic", lang)
            )
            return f"<b>{formatter.esc(msg)}</b>"

    async def cmd_callback(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        await query.answer()

        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)
        data = query.data

        if data == "cmd:list":
            self._clear_add_tracking_context(context)
            await self._show_order_list(chat_id, update, context, lang)
        elif data == "cmd:add":
            await self._show_add_carrier_selection(chat_id, update, context, lang)
        elif data == "cmd:menu":
            self._clear_add_tracking_context(context)
            await self._send_or_edit(
                update=update,
                context=context,
                chat_id=chat_id,
                text=f"<b>{formatter.esc(self._i18n.t('help_intro', lang))}</b>",
                reply_markup=self._build_main_keyboard(lang),
                parse_mode="HTML",
            )
        elif data and data.startswith("filter:"):
            await self._handle_filter_callback(chat_id, update, context, lang, data)

    async def list_command(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)

        if update.message is not None:
            await self._delete_message_quietly(update.message)
        await self._show_order_list(chat_id, update, context, lang)

    async def _show_order_list(
        self,
        chat_id: int,
        update: Update,
        context: CallbackContext,
        lang: str,
        status_filter: str | None = None,
    ) -> None:
        trackings = self._service.list_trackings(chat_id, status_filter)

        # Get all trackings for filter counts
        all_trackings = self._service.list_trackings(chat_id)
        active_count = len(
            [t for t in all_trackings if t.is_active]
        )
        delivered_count = len(
            [t for t in all_trackings if t.last_status == "DELIVERED"]
        )
        failed_count = len(
            [t for t in all_trackings if t.last_status == "FAILED"]
        )

        if not trackings:
            text = f"<b>{formatter.esc(self._i18n.t('list_empty', lang))}</b>"
            keyboard = InlineKeyboardMarkup(
                [[InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:menu")]]
            )
            await self._send_or_edit(update, context, chat_id, text, keyboard, parse_mode="HTML")
            return

        # Build header with filter label if filtering
        if status_filter:
            filter_label = self._i18n.t(f"filter_label_{status_filter}", lang)
            header = self._i18n.t("list_header_filtered", lang, filter=filter_label)
        else:
            header = self._i18n.t("list_header", lang)

        text = f"<b>{formatter.esc(header)}</b>\n\n"
        text += f"<i>{formatter.esc(self._i18n.t('tap_order_hint', lang))}</i>"
        buttons = []
        for tracking in trackings:
            status_icon = formatter.status_icon(tracking.last_status)
            code_1, code_2, code_3 = formatter.split_tracking_code_for_buttons(tracking.tracking_code)
            buttons.append(
                [
                    InlineKeyboardButton(status_icon, callback_data=f"order:{tracking.id}"),
                    InlineKeyboardButton(code_1, callback_data=f"order:{tracking.id}"),
                    InlineKeyboardButton(code_2, callback_data=f"order:{tracking.id}"),
                    InlineKeyboardButton(code_3, callback_data=f"order:{tracking.id}"),
                    InlineKeyboardButton("🗑️", callback_data=f"remove:{tracking.id}"),
                ]
            )

        # Filter buttons — 1 row, icon + count only
        buttons.append([
            InlineKeyboardButton(f"📋 {len(all_trackings)}", callback_data="filter:all"),
            InlineKeyboardButton(f"🔔 {active_count}",       callback_data="filter:active"),
            InlineKeyboardButton(f"✅ {delivered_count}",    callback_data="filter:delivered"),
            InlineKeyboardButton(f"❌ {failed_count}",       callback_data="filter:failed"),
        ])
        buttons.append([InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:menu")])
        keyboard = InlineKeyboardMarkup(buttons)

        await self._send_or_edit(update, context, chat_id, text, keyboard, parse_mode="HTML")

    async def _handle_filter_callback(
        self,
        chat_id: int,
        update: Update,
        context: CallbackContext,
        lang: str,
        data: str,
    ) -> None:
        """Handle filter selection callback."""
        filter_type = data.split(":")[-1]  # Extract filter type from callback data
        
        # Map filter type to status filter parameter
        status_filter = None if filter_type == "all" else filter_type
        
        await self._show_order_list(chat_id, update, context, lang, status_filter)

    async def filter_callback(self, update: Update, context: CallbackContext) -> None:
        """Public callback handler for filter selection."""
        query = update.callback_query
        await query.answer()
        
        chat_id = query.message.chat_id
        lang = self._get_user_lang(context)
        data = query.data
        
        await self._handle_filter_callback(chat_id, update, context, lang, data)

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

        text = f"<b>{formatter.esc(self._i18n.t('help_order_detail', lang))}</b>\n\n"
        text += f"🔖 {formatter.format_labeled_item(self._i18n.t('detail_code', lang, code=tracking.tracking_code), as_code=True)}\n"
        text += f"🚚 {formatter.format_labeled_item(self._i18n.t('detail_carrier', lang, carrier=tracking.carrier.name))}\n"
        status_icon = formatter.status_icon(tracking.last_status)
        text += f"{status_icon} {formatter.format_labeled_item(self._i18n.t('detail_status', lang, status=self._i18n.status(tracking.last_status, lang)))}\n"

        events = self._service.get_tracking_events(chat_id, tracking_id)
        if events:
            latest = events[-1]
            if latest.location:
                text += f"📍 {formatter.format_labeled_item(self._i18n.t('detail_location', lang, location=latest.location[:TIMELINE_LOCATION_MAX_LEN]), as_italic=True)}\n"
            if latest.event_time:
                formatted_time = formatter.format_datetime_local(latest.event_time, "%d/%m/%Y %H:%M") if isinstance(latest.event_time, datetime) else str(latest.event_time)
                text += f"🕒 {formatter.format_labeled_item(self._i18n.t('detail_time', lang, time=formatted_time), as_code=True)}"

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
                [
                    InlineKeyboardButton(
                        self._i18n.t(
                            "btn_notification_off" if tracking.notification_enabled else "btn_notification_on",
                            lang,
                        ),
                        callback_data=f"order_notify:{tracking_id}",
                    )
                ],
                [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:list")],
            ]
        )

        await self._safe_edit_message_text(query, text, reply_markup=keyboard, parse_mode="HTML")

    async def order_notification_callback(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        chat_id = update.effective_chat.id
        tracking_id = int(query.data.split(":")[-1])
        enabled = self._service.toggle_tracking_notification(chat_id, tracking_id)
        if enabled is None:
            await query.answer(
                self._i18n.t("order_not_found", self._get_user_lang(context)),
                show_alert=True,
            )
            return
        await self.order_callback(update, context)

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
            f"<b>{formatter.esc(self._i18n.t('help_timeline_title', lang))}</b>\n"
            f"📦 <code>{formatter.esc(tracking.tracking_code)}</code>\n"
            f"🚚 {formatter.esc(tracking.carrier.name)}\n\n"
        )

        if not page_events:
            text += f"<i>{formatter.esc(self._i18n.t('timeline_empty', lang))}</i>\n\n"

        for i, event in enumerate(page_events):
            event_num = start_idx + i + 1
            formatted_time = formatter.format_datetime_local(event.event_time, "%d/%m %H:%M") if isinstance(event.event_time, datetime) else str(event.event_time)
            status_text = self._i18n.status(event.status, lang)
            status_icon = formatter.status_icon(event.status)
            text += f"<b>{event_num}.</b> 🕒 <code>{formatter.esc(formatted_time)}</code> • {status_icon} <b>{formatter.esc(status_text)}</b>\n"
            if event.location:
                text += f"📍 <i>{formatter.esc(event.location[:TIMELINE_LOCATION_MAX_LEN])}</i>\n"
            if event.description:
                text += f"↳ {formatter.esc(event.description[:TIMELINE_DESCRIPTION_MAX_LEN])}\n"
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

    async def add_command(self, update: Update, context: CallbackContext) -> int:
        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)

        if update.message is not None:
            await self._delete_message_quietly(update.message)
        await self._show_add_carrier_selection(chat_id, update, context, lang)

        return WAITING_FOR_TRACKING_CODE

    async def _show_add_carrier_selection(self, chat_id: int, update: Update, context: CallbackContext, lang: str) -> None:
        text = f"<b>{formatter.esc(self._i18n.t('add_select_carrier', lang))}</b>"

        buttons = []
        for carrier_code, carrier_name in [
            ("jtexpress", "JT Express"),
            ("shopeeexpress", "Shopee Express"),
            ("ghn", "Giao Hàng Nhanh"),
        ]:
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

        context.user_data[ADD_WAITING_CARRIER] = carrier
        conxt.user_data[ADD_WAITING_CHAT_ID] = chat_id

        text = self._i18n.t("add_enter_code", lang)
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:add")]]
        )

        await self._safe_edit_message_text(
            query,
            f"<b>{formatter.esc(text)}</b>\n\n🔎 <i>{formatter.esc(self._i18n.t('example_label', lang))}:</i> <code>SPXVN123456789</code>",
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        return WAITING_FOR_TRACKING_CODE

    async def add_tracking_message(self, update: Update, context: CallbackContext) -> int:
        if context.user_data.get(ADD_WAITING_CARRIER) is None:
            return ConversationHandler.END

        if update.message is None:
            return ConversationHandler.END

        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)
        user_input = update.message.text.strip()
        carrier = context.user_data.get(ADD_WAITING_CARRIER)

        # Special handling for JT Express - check if waiting for phone digits
        if context.user_data.get(ADD_WAITING_JT_PHONE):
            # User is providing the 4-digit phone number
            if not re.match(r'^\d{4}$', user_input):
                await self._delete_message_quietly(update.message)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"<b>{formatter.esc(self._i18n.t('jt_phone_invalid', lang))}</b>\n\n🔎 <i>{formatter.esc(self._i18n.t('example_label', lang))}:</i> <code>4128</code>",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:add")]]),
                    parse_mode="HTML",
                )
                return WAITING_FOR_TRACKING_CODE
            
            # Combine order code with phone digits
            order_code = context.user_data[ADD_WAITING_JT_PHONE]
            tracking_code = f"{order_code}-{user_input}"
            text = self._build_add_tracking_result_text(chat_id, lang, tracking_code, carrier)
            
            self._clear_add_tracking_context(context)
            await self._delete_message_quietly(update.message)
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=self._build_main_keyboard(lang),
                parse_mode="HTML",
            )
            return ConversationHandler.END

        # Check if JT Express and missing phone digits
        if carrier == "jtexpress":
            # Check if user provided format: code-phone (e.g., "842608057049-4128")
            if "-" in user_input:
                parts = user_input.split("-")
                if len(parts) == 2 and re.match(r'^\d{4}$', parts[1]):
                    # Valid format, proceed
                    tracking_code = user_input
                else:
                    # Invalid format
                    await self._delete_message_quietly(update.message)
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"<b>{formatter.esc(self._i18n.t('jt_format_invalid', lang))}</b>\n\n🔎 <i>{formatter.esc(self._i18n.t('example_label', lang))}:</i> <code>842608057049-4128</code>",
                        reply_markup=self._build_main_keyboard(lang),
                        parse_mode="HTML",
                    )
                    return ConversationHandler.END
            else:
                # Only order code provided, ask for phone digits
                context.user_data[ADD_WAITING_JT_PHONE] = user_input
                await self._delete_message_quietly(update.message)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"<b>{formatter.esc(self._i18n.t('jt_enter_phone', lang))}</b>\n\n🔎 <i>{formatter.esc(self._i18n.t('example_label', lang))}:</i> <code>4128</code>",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:add")]]),
                    parse_mode="HTML",
                )
                return WAITING_FOR_TRACKING_CODE
        else:
            tracking_code = user_input

        text = self._build_add_tracking_result_text(chat_id, lang, tracking_code, carrier)

        self._clear_add_tracking_context(context)
        await self._delete_message_quietly(update.message)
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=self._build_main_keyboard(lang),
            parse_mode="HTML",
        )

        return ConversationHandler.END

    async def auto_add_shopee_from_message(self, update: Update, context: CallbackContext) -> None:
        """Auto-add tracking when user sends Shopee tracking code."""
        if update.message is None:
            return

        # If user is in interactive add flow, keep current behavior unchanged.
        if context.user_data.get(ADD_WAITING_CARRIER) is not None:
            return

        raw_text = update.message.text or ""
        match = re.match(r"^\s*(SPXVN[0-9A-Z]+)", raw_text, flags=re.IGNORECASE)
        if not match:
            return

        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)
        tracking_code = match.group(1).upper()

        text = self._build_add_tracking_result_text(chat_id, lang, tracking_code, "shopeeexpress")
        await self._delete_message_quietly(update.message)

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=self._build_main_keyboard(lang),
            parse_mode="HTML",
        )

    async def auto_add_from_message(self, update: Update, context: CallbackContext) -> None:
        """Auto-add tracking when user sends any valid tracking code."""
        if update.message is None:
            return

        # If user is in interactive add flow, skip auto-add
        if context.user_data.get(ADD_WAITING_CARRIER) is not None:
            return

        raw_text = (update.message.text or "").strip()
        if not raw_text or len(raw_text) > 20:  # Reasonable length check
            return

        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)

        # Try to detect carrier
        from app.services.tracking import TrackingService
        carrier = TrackingService.detect_carrier(raw_text)
        
        if not carrier:
            return  # Not a recognized tracking code

        tracking_code = raw_text.upper()
        text = self._build_add_tracking_result_text(chat_id, lang, tracking_code, carrier)
        await self._delete_message_quietly(update.message)

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=self._build_main_keyboard(lang),
            parse_mode="HTML",
        )

    async def remove_command(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)

        trackings = self._service.list_trackings(chat_id)

        if not trackings:
            text = f"<b>{formatter.esc(self._i18n.t('list_empty', lang))}</b>"
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
            text=f"<b>{formatter.esc(self._i18n.t('remove_select_prompt', lang))}</b>",
            reply_markup=keyboard,
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
