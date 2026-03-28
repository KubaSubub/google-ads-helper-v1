"""Conversion Value Rule model — adjust conversion values by audience/device/location."""

from sqlalchemy import Column, Integer, BigInteger, Float, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class ConversionValueRule(Base):
    __tablename__ = "conversion_value_rules"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    google_rule_id = Column(String(50), nullable=False)
    resource_name = Column(String(300), nullable=True)

    # Condition
    condition_type = Column(String(30), nullable=True)  # AUDIENCE, DEVICE, GEO_LOCATION
    condition_value = Column(String(500), nullable=True)  # Audience name, device type, location

    # Action
    action_type = Column(String(30), nullable=True)  # ADD, MULTIPLY
    action_value_micros = Column(BigInteger, nullable=True)  # Used when action_type == ADD (micros)
    action_multiplier = Column(Float, nullable=True)  # Used when action_type == MULTIPLY

    status = Column(String(20), default="ENABLED")

    __table_args__ = (
        UniqueConstraint("client_id", "google_rule_id", name="uq_conversion_value_rule"),
    )

    client = relationship("Client")
