"""Administrative dashboard and management handlers."""
from __future__ import annotations

from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from app.handlers.base_handler import BaseHandler
from app.utils import formatter

PAGE_SIZE = 10


class AdminHandler(BaseHandler):
    async def admin_command(self, update: Update, context: CallbackContext) -> None:
        chat_id = update.effective_chat.id
        telegram_user = update.effective_user
        self._service.ensure_user(
            chat_id,
            telegram_username=telegram_user.username if telegram_user else None,
            display_name=telegram_user.full_name if telegram_user else None,
        )
        if not self._service.is_admin(chat_id):
            await update.message.reply_text(self._i18n.t("admin_forbidden", self._get_user_lang(context)))
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
            await self._show_dashboard(update, context)
        elif action == "users":
            await self._show_users(update, context, int(parts[2]) if len(parts) > 2 else 0)
        elif action == "user":
            await self._show_user(update, context, int(parts[2]), int(parts[3]))
        elif action == "toggle_user_admin":
            user_id, page = int(parts[2]), int(parts[3])
            user = self._service.admin_get_user(user_id)
            if user and user["chat_id"] != chat_id:
                self._service.admin_toggle_user_admin(user_id)
            await self._show_user(update, context, user_id, page)
        elif action == "orders":
            await self._show_orders(update, context, int(parts[2]) if len(parts) > 2 else 0)
        elif action == "order":
            await self._show_order(update, context, int(parts[2]), int(parts[3]))
        elif action == "toggle_order":
            order_id, page = int(parts[2]), int(parts[3])
            self._service.admin_toggle_order_active(order_id)
            await self._show_order(update, context, order_id, page)

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
            [InlineKeyboardButton(self._i18n.t("admin_refresh", lang), callback_data="admin:refresh")],
            [InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="cmd:menu")],
        ])
        await self._send_or_edit(update, context, update.effective_chat.id, text, keyboard, "HTML")

    async def _show_users(self, update: Update, context: CallbackContext, page: int) -> None:
        lang = self._get_user_lang(context)
        users, total = self._service.admin_list_users(page * PAGE_SIZE, PAGE_SIZE)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = min(max(page, 0), pages - 1)
        if page * PAGE_SIZE >= total and total:
            users, _ = self._service.admin_list_users(page * PAGE_SIZE, PAGE_SIZE)
        buttons = [[InlineKeyboardButton(
            f"{'🛡️' if u['is_admin'] else '👤'} {u['display_name'] or u['username'] or u['chat_id']} · 📦 {u['order_count']}",
            callback_data=f"admin:user:{u['id']}:{page}",
        )] for u in users]
        buttons.append(self._nav("users", page, pages))
        buttons.append([InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data="admin:home")])
        text = f"<b>{formatter.esc(self._i18n.t('admin_user_list', lang))}</b>\n{page + 1}/{pages} · {total}"
        await self._safe_edit_message_text(update.callback_query, text, InlineKeyboardMarkup(buttons), "HTML")

    async def _show_user(self, update: Update, context: CallbackContext, user_id: int, page: int) -> None:
        lang = self._get_user_lang(context)
        user = self._service.admin_get_user(user_id)
        if user is None:
            await self._show_users(update, context, page)
            return
        created = self._format_date(user["created_at"])
        text = (
            f"<b>{formatter.esc(self._i18n.t('admin_user_detail', lang))}</b>\n\n"
            f"ID: <code>{user['id']}</code>\n"
            f"Name: <b>{formatter.esc(user['display_name'] or '-')}</b>\n"
            f"Username: <code>{formatter.esc('@' + user['username'] if user['username'] else '-')}</code>\n"
            f"Chat ID: <code>{user['chat_id']}</code>\n"
            f"Admin: <b>{'Yes' if user['is_admin'] else 'No'}</b>\n"
            f"📦 {user['order_count']} · 🔔 {user['active_order_count']}\n🕒 {formatter.esc(created)}"
        )
        toggle_key = "admin_revoke_admin" if user["is_admin"] else "admin_grant_admin"
        buttons = []
        if user["chat_id"] != update.effective_chat.id:
            buttons.append([InlineKeyboardButton(
                self._i18n.t(toggle_key, lang), callback_data=f"admin:toggle_user_admin:{user_id}:{page}"
            )])
        buttons.append([InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data=f"admin:users:{page}")])
        await self._safe_edit_message_text(update.callback_query, text, InlineKeyboardMarkup(buttons), "HTML")

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
        await self._safe_edit_message_text(update.callback_query, text, InlineKeyboardMarkup(buttons), "HTML")

    async def _show_order(self, update: Update, context: CallbackContext, order_id: int, page: int) -> None:
        lang = self._get_user_lang(context)
        order = self._service.admin_get_order(order_id)
        if order is None:
            await self._show_orders(update, context, page)
            return
        text = (
            f"<b>{formatter.esc(self._i18n.t('admin_order_detail', lang))}</b>\n\n"
            f"ID: <code>{order['id']}</code>\n📦 <code>{formatter.esc(order['tracking_code'])}</code>\n"
            f"👤 <code>{order['chat_id']}</code>\n🚚 {formatter.esc(order['carrier'])}\n"
            f"Status: <b>{formatter.esc(order['status'])}</b>\nEvents: {order['event_count']}\n"
            f"Active: <b>{'Yes' if order['is_active'] else 'No'}</b>"
        )
        buttons = []
        if order["status"] != "DELIVERED":
            toggle_key = "admin_pause_order" if order["is_active"] else "admin_resume_order"
            buttons.append([InlineKeyboardButton(
                self._i18n.t(toggle_key, lang),
                callback_data=f"admin:toggle_order:{order_id}:{page}",
            )])
        buttons.append([
            InlineKeyboardButton(self._i18n.t("btn_back", lang), callback_data=f"admin:orders:{page}")
        ])
        keyboard = InlineKeyboardMarkup(buttons)
        await self._safe_edit_message_text(update.callback_query, text, keyboard, "HTML")

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
        return formatter.format_datetime_local(value, "%d/%m/%Y %H:%M") if isinstance(value, datetime) else "-"
