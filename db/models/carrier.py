from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from db.models.base import Base


class Carrier(Base):
    """Carrier model"""

    __tablename__ = "carriers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)

    trackings = relationship("Tracking", back_populates="carrier")

    def __repr__(self) -> str:
        return f"<Carrier(code={self.code}, name={self.name})>"
