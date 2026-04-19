from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from db.models.base import Base, utcnow


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
        default=utcnow,
        nullable=False,
    )

    tracking = relationship("Tracking", back_populates="events")

    __table_args__ = (
        UniqueConstraint("tracking_id", "event_hash", name="uq_tracking_event_hash"),
    )

    def __repr__(self) -> str:
        return f"<TrackingEvent(id={self.id}, status={self.status}, time={self.event_time})>"
