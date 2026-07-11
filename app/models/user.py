from sqlalchemy import Boolean, Column, DateTime, Integer, String, false
from sqlalchemy.orm import relationship

from app.models.base import Base, utcnow


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_chat_id = Column(Integer, unique=True, nullable=False, index=True)
    telegram_username = Column(String(100), nullable=True)
    display_name = Column(String(200), nullable=True)
    is_admin = Column(Boolean, default=False, server_default=false(), nullable=False)
    credits = Column(Integer, default=100, server_default="100", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    trackings = relationship("Tracking", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, chat_id={self.telegram_chat_id})>"
