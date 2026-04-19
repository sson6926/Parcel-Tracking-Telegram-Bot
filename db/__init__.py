from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base

__all__ = ["create_session_factory", "init_db"]

_engines: dict[str, Engine] = {}


def _get_or_create_engine(database_url: str) -> Engine:
    if database_url not in _engines:
        # Normalize mysql:// → mysql+pymysql://
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
