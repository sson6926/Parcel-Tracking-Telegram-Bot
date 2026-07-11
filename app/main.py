#!/usr/bin/env python3
"""Telegram Bot entry point."""

import asyncio
import logging
import warnings

from dotenv import load_dotenv
import sentry_sdk
from telegram import Update
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.warnings import PTBUserWarning

from app.config.settings import get_bot_token, get_check_interval, get_database_url, setup_logging, setup_sentry
from app.i18n import I18n
from app.database import create_session_factory, init_db
from app.handlers import AdminHandler, StartHandler, HelpHandler, LanguageHandler, TrackingHandler
from app.scheduler.tracking import TrackingScheduler
from app.services.tracking import TrackingService

logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: CallbackContext) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    if context.error:
        sentry_sdk.capture_exception(context.error)
    if update and update.callback_query:
        try:
            await update.callback_query.answer("An error occurred. Please try again.", show_alert=False)
        except Exception as e:
            logger.error("Failed to answer callback: %s", e)
    elif update and update.message:
        try:
            await update.message.reply_text("An error occurred. Please try again.")
        except Exception as e:
            logger.error("Failed to send error message: %s", e)


async def noop_callback(update: Update, context: CallbackContext) -> None:
    await update.callback_query.answer()


def main() -> None:
    load_dotenv()
    setup_logging()
    setup_sentry()

    bot_token = get_bot_token()
    database_url = get_database_url()
    check_interval = get_check_interval()

    logger.info("Initializing database...")
    init_db(database_url)
    session_factory = create_session_factory(database_url)

    logger.info("Loading i18n...")
    i18n = I18n()

    logger.info("Initializing services...")
    tracking_service = TrackingService(session_factory, check_interval)
    tracking_service.seed_carriers()

    logger.info("Building bot application...")
    application = Application.builder().token(bot_token).build()

    start_handler = StartHandler(i18n, tracking_service)
    help_handler = HelpHandler(i18n, tracking_service)
    lang_handler = LanguageHandler(i18n, tracking_service)
    tracking_handler = TrackingHandler(i18n, tracking_service)
    admin_handler = AdminHandler(i18n, tracking_service)

    application.add_handler(CommandHandler("start", start_handler.start_command))
    application.add_handler(CommandHandler("help", help_handler.help_command))
    application.add_handler(CommandHandler("list", tracking_handler.list_command))
    application.add_handler(CommandHandler("remove", tracking_handler.remove_command))
    application.add_handler(CommandHandler("lang", lang_handler.lang_command))
    application.add_handler(CommandHandler("admin", admin_handler.admin_command))

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handler.broadcast_message),
        group=-1,
    )

    application.add_handler(CallbackQueryHandler(help_handler.help_callback, pattern="^help:"))
    application.add_handler(CallbackQueryHandler(lang_handler.lang_callback, pattern="^lang:"))
    application.add_handler(CallbackQueryHandler(tracking_handler.cmd_callback, pattern="^cmd:"))
    application.add_handler(CallbackQueryHandler(tracking_handler.order_callback, pattern="^order:[0-9]+$"))
    application.add_handler(CallbackQueryHandler(tracking_handler.order_notification_callback, pattern="^order_notify:[0-9]+$"))
    application.add_handler(CallbackQueryHandler(tracking_handler.order_timeline_callback, pattern="^order_timeline:"))
    application.add_handler(CallbackQueryHandler(tracking_handler.remove_callback, pattern="^remove:"))
    application.add_handler(CallbackQueryHandler(noop_callback, pattern="^noop"))
    application.add_handler(CallbackQueryHandler(admin_handler.admin_callback, pattern="^admin:"))
    application.add_handler(CallbackQueryHandler(start_handler.mission_callback, pattern="^info:mission$"))

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=PTBUserWarning)
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("add", tracking_handler.add_command),
                CallbackQueryHandler(tracking_handler.add_carrier_callback, pattern="^add_carrier:"),
            ],
            states={
                1: [
                    CallbackQueryHandler(tracking_handler.add_carrier_callback, pattern="^add_carrier:"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, tracking_handler.add_tracking_message),
                ],
            },
            fallbacks=[CommandHandler("start", start_handler.start_command)],
            per_message=False,
        )
    application.add_handler(conv_handler)

    # Auto-add tracking from message (for all carriers)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            tracking_handler.auto_add_from_message,
        )
    )

    application.add_error_handler(error_handler)

    scheduler = TrackingScheduler(session_factory, tracking_service, application=application)

    async def post_init(app) -> None:
        scheduler.set_event_loop(asyncio.get_event_loop())
        logger.info("Event loop captured for scheduler notifications")

    application.post_init = post_init
    scheduler.start()

    logger.info("Bot started")
    try:
        application.run_polling(allowed_updates=["message", "callback_query"])
    finally:
        scheduler.stop()


if __name__ == "__main__":
    main()
