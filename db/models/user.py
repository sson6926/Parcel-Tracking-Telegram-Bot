from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import relationship

from db.models.base import Base, utcnow


class User(Base):
    """User model"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_chat_id = Column(Integer, unique=True, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )

    trackings = relationship("Tracking", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, chat_id={self.telegram_chat_id})>"
