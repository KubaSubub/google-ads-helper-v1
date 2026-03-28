"""Audience model — remarketing, in-market, affinity, custom audiences."""

from sqlalchemy import Column, Integer, BigInteger, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Audience(Base):
    __tablename__ = "audiences"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    google_audience_id = Column(String(50), nullable=False)
    resource_name = Column(String(300), nullable=True)

    name = Column(String(500), nullable=False)
    audience_type = Column(String(50), nullable=True)  # REMARKETING, IN_MARKET, AFFINITY, CUSTOM_INTENT, SIMILAR, COMBINED
    description = Column(String(2000), nullable=True)
    status = Column(String(20), default="ENABLED")
    member_count = Column(BigInteger, nullable=True)  # Estimated size

    __table_args__ = (
        UniqueConstraint("client_id", "google_audience_id", name="uq_audience"),
    )

    client = relationship("Client")
