from __future__ import annotations

import logging
import os


def get_bot_token() -> str:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is missing. Please set it in your .env file.")
    return token


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///tracking.db")


def get_check_interval() -> int:
    return int(os.getenv("CHECK_INTERVAL_MINUTES", "5"))


def setup_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger(__name__).info("Logging level set to %s", log_level)


def setup_sentry() -> None:
    import sentry_sdk
    from sentry_sdk.integrations.logging import LoggingIntegration

    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return

    environment = os.getenv("SENTRY_ENVIRONMENT", "production")
    release = os.getenv("SENTRY_RELEASE")

    try:
        traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0"))
    except ValueError:
        traces_sample_rate = 0.0

    send_default_pii = os.getenv("SENTRY_SEND_DEFAULT_PII", "false").strip().lower() in {"1", "true", "yes", "on"}

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=send_default_pii,
        enable_logs=True,
        integrations=[LoggingIntegration(level=logging.INFO, event_level=logging.WARNING)],
    )
