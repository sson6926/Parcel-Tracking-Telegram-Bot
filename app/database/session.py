from __future__ import annotations

from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

__all__ = ["create_session_factory", "init_db"]

_engines: dict[str, Engine] = {}


def _get_or_create_engine(database_url: str) -> Engine:
    if database_url not in _engines:
        url = database_url
        if url.startswith("mysql://"):
            url = url.replace("mysql://", "mysql+pymysql://", 1)
        _engines[database_url] = create_engine(
            url,
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return _engines[database_url]


def create_session_factory(database_url: str):
    engine = _get_or_create_engine(database_url)
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def init_db(database_url: str) -> None:
    engine = _get_or_create_engine(database_url)
    Base.metadata.create_all(bind=engine)
    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    if "is_admin" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT FALSE")
            )
    if "telegram_username" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN telegram_username VARCHAR(100)"))
    if "display_name" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN display_name VARCHAR(200)"))
    tracking_columns = {column["name"] for column in inspect(engine).get_columns("trackings")}
    if "notification_enabled" not in tracking_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE trackings ADD COLUMN notification_enabled "
                    "BOOLEAN NOT NULL DEFAULT TRUE"
                )
            )
    if "is_deleted" not in tracking_columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE trackings ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE")
            )
