#!/usr/bin/env python3
"""
Telegram Bot Main Entry Point
Supports both Webhook and Polling modes
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CallbackContext

from app.bot.handlers import TrackingHandlers
from app.core.i18n import I18n
from db import create_session_factory, init_db
from tracking.scheduler import TrackingScheduler
from tracking.service import TrackingService

logger = logging.getLogger(__name__)


async def error_handler(update: Update, context: CallbackContext) -> None:
    """Handle errors by logging them and alerting the user if possible."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    if update and update.callback_query:
        try:
            await update.callback_query.answer("An error occurred. Please try again.", show_alert=False)
        except Exception as e:
            logger.error(f"Failed to answer callback: {e}")
    elif update and update.message:
        try:
            await update.message.reply_text("An error occurred. Please try again.")
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")


async def noop_callback(update: Update, context: CallbackContext) -> None:
    """No-op callback for buttons that don't need to do anything."""
    await update.callback_query.answer()


def setup_logging() -> None:
    """Setup logging configuration"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger.info(f"Logging level set to {log_level}")


def main() -> None:
    """Main entry point"""
    load_dotenv()
    setup_logging()

    bot_token = os.getenv("BOT_TOKEN", "your-token-here")
    if bot_token == "your-token-here":
        raise RuntimeError("BOT_TOKEN is missing. Please set it in your .env file.")

    database_url = os.getenv("DATABASE_URL", "sqlite:///tracking.db")
    check_interval = int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))

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
    application.bot_data["i18n"] = i18n
    application.bot_data["tracking_service"] = tracking_service

    handlers = TrackingHandlers(i18n, tracking_service)

    # Register handlers in application
    from telegram.ext import (
        CallbackQueryHandler,
        CommandHandler,
        ConversationHandler,
        MessageHandler,
        filters,
    )

    # Command handlers
    application.add_handler(CommandHandler("start", handlers.start_command))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("list", handlers.list_command))
    application.add_handler(CommandHandler("remove", handlers.remove_command))
    application.add_handler(CommandHandler("lang", handlers.lang_command))

    # Callback handlers
    application.add_handler(CallbackQueryHandler(handlers.help_callback, pattern="^help:"))
    application.add_handler(CallbackQueryHandler(handlers.lang_callback, pattern="^lang:"))
    application.add_handler(CallbackQueryHandler(handlers.cmd_callback, pattern="^cmd:"))
    application.add_handler(CallbackQueryHandler(handlers.order_callback, pattern="^order:[0-9]+$"))
    application.add_handler(CallbackQueryHandler(handlers.order_timeline_callback, pattern="^order_timeline:"))
    application.add_handler(CallbackQueryHandler(handlers.remove_callback, pattern="^remove:"))
    application.add_handler(CallbackQueryHandler(noop_callback, pattern="^noop"))

    # Conversation handler for adding tracking
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("add", handlers.add_command),
            CallbackQueryHandler(handlers.add_carrier_callback, pattern="^add_carrier:"),
        ],
        states={
            1: [
                CallbackQueryHandler(handlers.add_carrier_callback, pattern="^add_carrier:"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.add_tracking_message),
            ],
        },
        fallbacks=[CommandHandler("start", handlers.start_command)],
    )
    application.add_handler(conv_handler)

    # Add error handler
    application.add_error_handler(error_handler)

    # Setup scheduler
    scheduler = TrackingScheduler(session_factory, tracking_service)
    scheduler.start()

    logger.info("Bot application started successfully")
    try:
        application.run_polling(allowed_updates=["message", "callback_query"])
    finally:
        scheduler.stop()


if __name__ == "__main__":
    main()
