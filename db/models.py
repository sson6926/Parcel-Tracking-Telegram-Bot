from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """User model"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_chat_id = Column(Integer, unique=True, nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    trackings = relationship("Tracking", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, chat_id={self.telegram_chat_id})>"


class Carrier(Base):
    """Carrier model"""

    __tablename__ = "carriers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)

    trackings = relationship("Tracking", back_populates="carrier")

    def __repr__(self) -> str:
        return f"<Carrier(code={self.code}, name={self.name})>"


class Tracking(Base):
    """Tracking model"""

    __tablename__ = "trackings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=False, index=True)
    tracking_code = Column(String(100), nullable=False, index=True)
    last_status = Column(String(50), default="CREATED", nullable=False)
    last_event_hash = Column(String(100), nullable=True)
    next_check_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="trackings")
    carrier = relationship("Carrier", back_populates="trackings")
    events = relationship("TrackingEvent", back_populates="tracking", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("user_id", "carrier_id", "tracking_code", name="uq_user_carrier_code"),)

    def __repr__(self) -> str:
        return f"<Tracking(id={self.id}, code={self.tracking_code}, status={self.last_status})>"


class TrackingEvent(Base):
    """Tracking event model"""

    __tablename__ = "tracking_events"

    id = Column(Integer, primary_key=True, index=True)
    tracking_id = Column(Integer, ForeignKey("trackings.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    description = Column(String(500), nullable=True)
    location = Column(String(200), nullable=True)
    event_time = Column(DateTime(timezone=True), nullable=False)
    event_hash = Column(String(100), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tracking = relationship("Tracking", back_populates="events")

    __table_args__ = (
        UniqueConstraint("tracking_id", "event_hash", name="uq_tracking_event_hash"),
    )

    def __repr__(self) -> str:
        return f"<TrackingEvent(id={self.id}, status={self.status}, time={self.event_time})>"
