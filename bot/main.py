#!/usr/bin/env python3
"""Telegram Bot entry point. Supports polling mode."""

import asyncio
import logging
import os
import warnings

from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
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

from app.bot.handlers import TrackingHandlers
from app.core.i18n import I18n
from db import create_session_factory, init_db
from tracking.scheduler import TrackingScheduler
from tracking.service import TrackingService

logger = logging.getLogger(__name__)


def setup_sentry() -> None:
    """Initialize Sentry if SENTRY_DSN is configured."""
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        logger.info("Sentry disabled (SENTRY_DSN is not set)")
        return

    environment = os.getenv("SENTRY_ENVIRONMENT", "production")
    release = os.getenv("SENTRY_RELEASE")

    try:
        traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0"))
    except ValueError:
        traces_sample_rate = 0.0

    send_default_pii_raw = os.getenv("SENTRY_SEND_DEFAULT_PII", "false").strip().lower()
    send_default_pii = send_default_pii_raw in {"1", "true", "yes", "on"}

    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.WARNING,
    )

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=send_default_pii,
        enable_logs=True,
        integrations=[sentry_logging],
    )
    logger.info(
        "Sentry initialized for environment '%s' (send_default_pii=%s)",
        environment,
        send_default_pii,
    )


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
    """No-op callback for buttons that don't need to do anything."""
    await update.callback_query.answer()


def setup_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logger.info("Logging level set to %s", log_level)


def main() -> None:
    load_dotenv()
    setup_logging()
    setup_sentry()

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
    # Suppress PTBUserWarning about per_message=False (expected behavior for this flow)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=PTBUserWarning)
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
            per_message=False,
        )
    application.add_handler(conv_handler)

    # Auto-add Shopee order when message starts with SPXVN...
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.Regex(r"(?i)^\s*SPXVN"),
            handlers.auto_add_shopee_from_message,
        )
    )

    application.add_error_handler(error_handler)

    scheduler = TrackingScheduler(session_factory, tracking_service, application=application)

    async def post_init(app) -> None:
        # Capture the running event loop so the background scheduler thread
        # can dispatch send_message coroutines into it via run_coroutine_threadsafe.
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
