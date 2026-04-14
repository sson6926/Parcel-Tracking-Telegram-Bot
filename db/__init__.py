from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base

__all__ = ["create_session_factory", "init_db"]

# Global engines to ensure consistency
_engines: dict[str, any] = {}


def create_session_factory(database_url: str):
    if database_url not in _engines:
        _engines[database_url] = create_engine(database_url, echo=False)
    
    engine = _engines[database_url]
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def init_db(database_url: str):
    if database_url not in _engines:
        _engines[database_url] = create_engine(database_url, echo=False)
    
    engine = _engines[database_url]
    Base.metadata.create_all(bind=engine)
