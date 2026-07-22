"""Administrative dashboard and management handlers."""
from __future__ import annotations

import logging
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ApplicationHandlerStop, CallbackContext

from app.handlers.base_handler import BaseHandler
from app.utils import formatter

logger = logging.getLogger(__name__)

PAGE_SIZE = 10
BROADCAST_WAITING_KEY = "admin_broadcast_waiting"
CREDITS_WAITING_KEY = "admin_credits_waiting"  # {"user_id": int, "page": int}


class AdminHandler(BaseHandler):

    # ------------------------------------------------------------------
    # Entry points
    # ------------------------------------------------------------------

    async def admin_command(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.effective_chat.id
        telegram_user = update.effective_user
        self._service.ensure_user(
            chat_id,
            telegram_username=telegram_user.username if telegram_user else None,
            display_name=telegram_user.full_name if telegram_user else None,
        )
        if not self._service.is_admin(chat_id):
            await update.message.reply_text(
                self._i18n.t("admin_forbidden", self._get_user_lang(context))
            )
            return
        await self._show_dashboard(update, context)

    async def admin_callback(self, update: Update, context: CallbackContext) -> None:
        query = update.callback_query
        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)
        if not self._service.is_admin(chat_id):
            await query.answer(self._i18n.t("admin_forbidden", lang), show_alert=True)
            return
        await query.answer()

        parts = query.data.split(":")
        action = parts[1]

        if action in {"home", "refresh"}:
            context.user_data.pop(BROADCAST_WAITING_KEY, None)
            context.user_data.pop(CREDITS_WAITING_KEY, None)
            await self._show_dashboard(update, context)

        elif action == "broadcast":
            context.user_data[BROADCAST_WAITING_KEY] = True
            await self._show_broadcast_prompt(update, context)

        elif action == "broadcast_cancel":
            context.user_data.pop(BROADCAST_WAITING_KEY, None)
            await self._show_dashboard(update, context)

        elif action == "users":
            page = int(parts[2]) if len(parts) > 2 else 0
            await self._show_users(update, context, page)

        elif action == "user":
            await self._show_user(update, context, int(parts[2]), int(parts[3]))

        elif action == "toggle_user_admin":
            user_id, page = int(parts[2]), int(parts[3])
            user = self._service.admin_get_user(user_id)
            if user and user["chat_id"] != chat_id:
                self._service.admin_toggle_user_admin(user_id)
            await self._show_user(update, context, user_id, page)

        elif action == "toggle_user_ban":
            user_id, page = int(parts[2]), int(parts[3])
            user = self._service.admin_get_user(user_id)
            if user and user["chat_id"] != chat_id:
                self._service.admin_toggle_user_banned(user_id)
            await self._show_user(update, context, user_id, page)

        elif action == "credits_prompt":
            user_id, page = int(parts[2]), int(parts[3])
            context.user_data[CREDITS_WAITING_KEY] = {"user_id": user_id, "page": page}
            await self._show_credits_prompt(update, context, user_id, page)

        elif action == "credits_cancel":
            context.user_data.pop(CREDITS_WAITING_KEY, None)
            user_id, page = int(parts[2]), int(parts[3])
            await self._show_user(update, context, user_id, page)

        elif action == "user_orders":
            user_id = int(parts[2])
            page = int(parts[3]) if len(parts) > 3 else 0
            back_page = int(parts[4]) if len(parts) > 4 else 0
            await self._show_user_orders(update, context, user_id, page, back_page)

        elif action == "orders":
            page = int(parts[2]) if len(parts) > 2 else 0
            await self._show_orders(update, context, page)

        elif action == "order":
            await self._show_order(update, context, int(parts[2]), int(parts[3]))

        elif action == "toggle_order":
            order_id, page = int(parts[2]), int(parts[3])
            self._service.admin_toggle_order_active(order_id)
            await self._show_order(update, context, order_id, page)

    # ------------------------------------------------------------------
    # Text message handler (broadcast / credits input)
    # ------------------------------------------------------------------

    async def broadcast_message(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.effective_chat.id
        lang = self._get_user_lang(context)

        # Credits adjustment input
        if context.user_data.get(CREDITS_WAITING_KEY):
            if update.message is None:
                return
            if not self._service.is_admin(chat_id):
                await update.message.reply_text(self._i18n.t("admin_forbidden", lang))
                raise ApplicationHandlerStop

            payload = context.user_data.pop(CREDITS_WAITING_KEY)
            user_id, page = payload["user_id"], payload["page"]
            raw = (update.message.text or "").strip()

            try:
                delta = int(raw)
            except ValueError:
                await update.message.reply_text(
                    f"<b>{formatter.esc(self._i18n.t('admin_credits_invalid', lang))}</b>",
                    parse_mode="HTML",
                )
                raise ApplicationHandlerStop

            new_balance = self._service.admin_adjust_user_credits(user_id, delta)
            sign = "+" if delta >= 0 else ""
            await update.message.reply_text(
                f"<b>{formatter.esc(self._i18n.t('admin_credits_updated', lang, delta=f'{sign}{delta}', balance=new_balance))}</b>",
                parse_mode="HTML",
            )
            await self._delete_message_quietly(update.message)
            raise ApplicationHandlerStop

        # Broadcast input
        if not context.user_data.get(BROADCAST_WAITING_KEY):
            return
        if update.message is None:
            return
        context.user_data.pop(BROADCAST_WAITING_KEY, None)
        if not self._service.is_admin(chat_id):
            await update.message.reply_text(self._i18n.t("admin_forbidden", lang))
            raise ApplicationHandlerStop

        message_text = update.message.text or ""
        recipient_ids = self._service.admin_get_broadcast_chat_ids()
        sent = 0
        failed = 0
        for recipient_id in recipient_ids:
            try:
                await context.bot.send_message(chat_id=recipient_id, text=message_text)
                sent += 1
            except TelegramError:
                failed += 1

        result = self._i18n.t("admin_broadcast_result", lang, sent=sent, failed=failed)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"<b>{formatter.esc(result)}</b>",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="admin:home")]]
            ),
            parse_mode="HTML",
        )
        raise ApplicationHandlerStop

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    async def _show_dashboard(self, update: Update, context: CallbackContext) -> None:
        lang = self._get_user_lang(context)
        stats = self._service.get_admin_dashboard_stats()
        text = (
            f"<b>{formatter.esc(self._i18n.t('admin_title', lang))}</b>\n\n"
            f"👥 {formatter.esc(self._i18n.t('admin_users', lang, value=stats['users']))}\n"
            f"🛡️ {formatter.esc(self._i18n.t('admin_admins', lang, value=stats['admins']))}\n"
            f"📦 {formatter.esc(self._i18n.t('admin_orders', lang, value=stats['orders']))}\n"
            f"🔔 {formatter.esc(self._i18n.t('admin_active_orders', lang, value=stats['active_orders']))}\n"
            f"✅ {formatter.esc(self._i18n.t('admin_delivered_orders', lang, value=stats['delivered_orders']))}\n"
            f"❌ {formatter.esc(self._i18n.t('admin_failed_orders', lang, value=stats['failed_orders']))}"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(self._i18n.t("admin_manage_users", lang), callback_data="admin:users:0")],
            [InlineKeyboardButton(self._i18n.t("admin_manage_orders", lang), callback_data="admin:orders:0")],
            [InlineKeyboardButton(self._i18n.t("admin_broadcast", lang), callback_data="admin:broadcast")],
            [InlineKeyboardButton(self._i18n.t("admin_refresh", lang), callback_data="admin:refresh")],
            [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:menu")],
        ])
        await self._send_or_edit(update, context, update.effective_chat.id, text, keyboard, "HTML")

    # ------------------------------------------------------------------
    # Broadcast
    # ------------------------------------------------------------------

    async def _show_broadcast_prompt(self, update: Update, context: CallbackContext) -> None:
        lang = self._get_user_lang(context)
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                self._i18n.t("admin_broadcast_cancel", lang),
                callback_data="admin:broadcast_cancel",
            )
        ]])
        await self._safe_edit_message_text(
            update.callback_query,
            f"<b>{formatter.esc(self._i18n.t('admin_broadcast_prompt', lang))}</b>",
            keyboard,
            "HTML",
        )

    # ------------------------------------------------------------------
    # User list
    # ------------------------------------------------------------------

    async def _show_users(self, update: Update, context: CallbackContext, page: int) -> None:
        lang = self._get_user_lang(context)
        users, total = self._service.admin_list_users(page * PAGE_SIZE, PAGE_SIZE)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(max(page, 0), pages - 1)
        if page * PAGE_SIZE >= total and total:
            users, _ = self._service.admin_list_users(page * PAGE_SIZE, PAGE_SIZE)

        buttons = []
        for u in users:
            ban_icon = "🚫" if u.get("is_banned") else ("🛡️" if u["is_admin"] else "👤")
            label = u["display_name"] or u["username"] or str(u["chat_id"])
            buttons.append([InlineKeyboardButton(
                f"{ban_icon} {label} · 💳 {u['credits']} · 📦 {u['order_count']}",
                callback_data=f"admin:user:{u['id']}:{page}",
            )])

        buttons.append(self._nav("users", page, pages))
        buttons.append([InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="admin:home")])
        text = f"<b>{formatter.esc(self._i18n.t('admin_user_list', lang))}</b>\n{page + 1}/{pages} · {total}"
        await self._safe_edit_message_text(
            update.callback_query, text, InlineKeyboardMarkup(buttons), "HTML"
        )

    # ------------------------------------------------------------------
    # User detail
    # ------------------------------------------------------------------

    async def _show_user(
        self, update: Update, context: CallbackContext, user_id: int, page: int
    ) -> None:
        lang = self._get_user_lang(context)
        user = self._service.admin_get_user(user_id)
        if user is None:
            await self._show_users(update, context, page)
            return

        created = self._format_date(user["created_at"])
        ban_status = "🚫 Banned" if user.get("is_banned") else "✅ Active"
        text = (
            f"<b>{formatter.esc(self._i18n.t('admin_user_detail', lang))}</b>\n\n"
            f"ID: <code>{user['id']}</code>\n"
            f"Name: <b>{formatter.esc(user['display_name'] or '-')}</b>\n"
            f"Username: <code>{formatter.esc('@' + user['username'] if user['username'] else '-')}</code>\n"
            f"Chat ID: <code>{user['chat_id']}</code>\n"
            f"Admin: <b>{'🛡️ Yes' if user['is_admin'] else 'No'}</b>\n"
            f"Status: <b>{ban_status}</b>\n"
            f"Credits: <b>{user['credits']}</b>\n"
            f"📦 {user['order_count']} orders · 🔔 {user['active_order_count']} active\n"
            f"🕒 {formatter.esc(created)}"
        )

        is_self = user["chat_id"] == update.effective_chat.id
        buttons = []

        # Admin toggle (cannot touch self)
        if not is_self:
            toggle_admin_key = "admin_revoke_admin" if user["is_admin"] else "admin_grant_admin"
            buttons.append([InlineKeyboardButton(
                self._i18n.t(toggle_admin_key, lang),
                callback_data=f"admin:toggle_user_admin:{user_id}:{page}",
            )])

        # Ban toggle (cannot touch self)
        if not is_self:
            ban_key = "admin_unban_user" if user.get("is_banned") else "admin_ban_user"
            buttons.append([InlineKeyboardButton(
                self._i18n.t(ban_key, lang),
                callback_data=f"admin:toggle_user_ban:{user_id}:{page}",
            )])

        # Credits adjustment
        buttons.append([InlineKeyboardButton(
            self._i18n.t("admin_adjust_credits", lang),
            callback_data=f"admin:credits_prompt:{user_id}:{page}",
        )])

        # View user's orders
        buttons.append([InlineKeyboardButton(
            self._i18n.t("admin_view_user_orders", lang),
            callback_data=f"admin:user_orders:{user_id}:0:{page}",
        )])

        buttons.append([InlineKeyboardButton(
            self._i18n.t("btn_back", lang),
            callback_data=f"admin:users:{page}",
        )])

        await self._safe_edit_message_text(
            update.callback_query, text, InlineKeyboardMarkup(buttons), "HTML"
        )

    # ------------------------------------------------------------------
    # Credits prompt
    # ------------------------------------------------------------------

    async def _show_credits_prompt(
        self,
        update: Update,
        context: CallbackContext,
        user_id: int,
        page: int,
    ) -> None:
        lang = self._get_user_lang(context)
        user = self._service.admin_get_user(user_id)
        current = user["credits"] if user else "?"
        text = (
            f"<b>{formatter.esc(self._i18n.t('admin_credits_prompt', lang))}</b>\n\n"
            f"{formatter.esc(self._i18n.t('admin_credits_current', lang, value=current))}\n\n"
            f"<i>{formatter.esc(self._i18n.t('admin_credits_hint', lang))}</i>"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                self._i18n.t("btn_back", lang),
                callback_data=f"admin:credits_cancel:{user_id}:{page}",
            )
        ]])
        await self._safe_edit_message_text(update.callback_query, text, keyboard, "HTML")

    # ------------------------------------------------------------------
    # User's orders
    # ------------------------------------------------------------------

    async def _show_user_orders(
        self,
        update: Update,
        context: CallbackContext,
        user_id: int,
        page: int,
        back_page: int,
    ) -> None:
        lang = self._get_user_lang(context)
        orders, total = self._service.admin_list_user_orders(user_id, page * PAGE_SIZE, PAGE_SIZE)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(max(page, 0), pages - 1)

        buttons = []
        for o in orders:
            icon = "🔔" if o["is_active"] else "⏸️"
            buttons.append([InlineKeyboardButton(
                f"{icon} {o['tracking_code']} · {o['carrier']}",
                callback_data=f"admin:order:{o['id']}:0",
            )])

        # Nav row
        prev_p = (page - 1) % pages
        next_p = (page + 1) % pages
        buttons.append([
            InlineKeyboardButton("⬅️", callback_data=f"admin:user_orders:{user_id}:{prev_p}:{back_page}"),
            InlineKeyboardButton(f"[{page + 1}/{pages}]", callback_data="noop"),
            InlineKeyboardButton("➡️", callback_data=f"admin:user_orders:{user_id}:{next_p}:{back_page}"),
        ])
        buttons.append([InlineKeyboardButton(
            self._i18n.t("btn_back", lang),
            callback_data=f"admin:user:{user_id}:{back_page}",
        )])

        user = self._service.admin_get_user(user_id)
        name = user["display_name"] or user["username"] or str(user["chat_id"]) if user else str(user_id)
        text = (
            f"<b>{formatter.esc(self._i18n.t('admin_user_orders_title', lang, name=name))}</b>\n"
            f"{page + 1}/{pages} · {total}"
        )
        await self._safe_edit_message_text(
            update.callback_query, text, InlineKeyboardMarkup(buttons), "HTML"
        )

    # ------------------------------------------------------------------
    # Global order list
    # ------------------------------------------------------------------

    async def _show_orders(self, update: Update, context: CallbackContext, page: int) -> None:
        lang = self._get_user_lang(context)
        orders, total = self._service.admin_list_orders(page * PAGE_SIZE, PAGE_SIZE)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(max(page, 0), pages - 1)
        if page * PAGE_SIZE >= total and total:
            orders, _ = self._service.admin_list_orders(page * PAGE_SIZE, PAGE_SIZE)

        buttons = [[InlineKeyboardButton(
            f"{'🔔' if o['is_active'] else '⏸️'} {o['tracking_code']}",
            callback_data=f"admin:order:{o['id']}:{page}",
        )] for o in orders]
        buttons.append(self._nav("orders", page, pages))
        buttons.append([InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="admin:home")])
        text = f"<b>{formatter.esc(self._i18n.t('admin_order_list', lang))}</b>\n{page + 1}/{pages} · {total}"
        await self._safe_edit_message_text(
            update.callback_query, text, InlineKeyboardMarkup(buttons), "HTML"
        )

    # ------------------------------------------------------------------
    # Order detail
    # ------------------------------------------------------------------

    async def _show_order(
        self, update: Update, context: CallbackContext, order_id: int, page: int
    ) -> None:
        lang = self._get_user_lang(context)
        order = self._service.admin_get_order(order_id)
        if order is None:
            await self._show_orders(update, context, page)
            return
        created = self._format_date(order.get("created_at"))
        text = (
            f"<b>{formatter.esc(self._i18n.t('admin_order_detail', lang))}</b>\n\n"
            f"ID: <code>{order['id']}</code>\n"
            f"📦 <code>{formatter.esc(order['tracking_code'])}</code>\n"
            f"👤 <code>{order['chat_id']}</code>\n"
            f"🚚 {formatter.esc(order['carrier'])}\n"
            f"Status: <b>{formatter.esc(order['status'])}</b>\n"
            f"Events: {order['event_count']}\n"
            f"Active: <b>{'Yes' if order['is_active'] else 'No'}</b>\n"
            f"🕒 {formatter.esc(created)}"
        )
        buttons = []
        if order["status"] != "DELIVERED":
            toggle_key = "admin_pause_order" if order["is_active"] else "admin_resume_order"
            buttons.append([InlineKeyboardButton(
                self._i18n.t(toggle_key, lang),
                callback_data=f"admin:toggle_order:{order_id}:{page}",
            )])
        buttons.append([InlineKeyboardButton(
            self._i18n.t("btn_back", lang),
            callback_data=f"admin:orders:{page}",
        )])
        await self._safe_edit_message_text(
            update.callback_query, text, InlineKeyboardMarkup(buttons), "HTML"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _nav(section: str, page: int, pages: int) -> list[InlineKeyboardButton]:
        previous = (page - 1) % pages
        following = (page + 1) % pages
        return [
            InlineKeyboardButton("⬅️", callback_data=f"admin:{section}:{previous}"),
            InlineKeyboardButton(f"[{page + 1}/{pages}]", callback_data="noop"),
            InlineKeyboardButton("➡️", callback_data=f"admin:{section}:{following}"),
        ]

    @staticmethod
    def _format_date(value: object) -> str:
        return (
            formatter.format_datetime_local(value, "%d/%m/%Y %H:%M")
            if isinstance(value, datetime)
            else "-"
        )
