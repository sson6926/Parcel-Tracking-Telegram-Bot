from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, false, true
from sqlalchemy.orm import relationship

from app.models.base import Base, utcnow


class Tracking(Base):
    __tablename__ = "trackings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    carrier_id = Column(Integer, ForeignKey("carriers.id"), nullable=False, index=True)
    tracking_code = Column(String(100), nullable=False, index=True)
    last_status = Column(String(50), default="CREATED", nullable=False)
    last_event_hash = Column(String(100), nullable=True)
    next_check_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_deleted = Column(Boolean, default=False, server_default=false(), nullable=False)
    notification_enabled = Column(Boolean, default=True, server_default=true(), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="trackings")
    carrier = relationship("Carrier", back_populates="trackings")
    events = relationship("TrackingEvent", back_populates="tracking", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("user_id", "carrier_id", "tracking_code", name="uq_user_carrier_code"),)

    def __repr__(self) -> str:
        return f"<Tracking(id={self.id}, code={self.tracking_code}, status={self.last_status})>"
