"""Legacy module kept for backward compatibility with Procfile and deployment scripts.
Use db.__init__ (create_session_factory, init_db) for new code.
"""
import os

from db import create_session_factory, init_db as _init_db
from db.models import Base  # noqa: F401 – re-exported for convenience

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tracking.db")

SessionLocal = create_session_factory(DATABASE_URL)


def init_db() -> None:
    """Initialize database and create all tables."""
    _init_db(DATABASE_URL)
