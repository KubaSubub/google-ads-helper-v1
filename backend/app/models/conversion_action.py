"""ConversionAction model for GAP 2A-2D: Conversion Data Quality Audit."""

from sqlalchemy import Column, Integer, BigInteger, Float, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class ConversionAction(Base):
    __tablename__ = "conversion_actions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    google_conversion_action_id = Column(String(50), nullable=False)
    name = Column(String(500), nullable=False)
    category = Column(String(50), nullable=True)       # PURCHASE, LEAD, SIGNUP, etc.
    status = Column(String(20), nullable=False)         # ENABLED, REMOVED, HIDDEN
    type = Column(String(50), nullable=True)            # WEBPAGE, UPLOAD_CLICKS, etc.
    primary_for_goal = Column(Boolean, default=False)
    counting_type = Column(String(30), nullable=True)   # ONE_PER_CLICK, MANY_PER_CLICK
    value_settings_default_value = Column(Float, nullable=True)
    value_settings_always_use_default = Column(Boolean, nullable=True)
    attribution_model = Column(String(50), nullable=True)  # GOOGLE_ADS_LAST_CLICK, DATA_DRIVEN, etc.
    click_through_lookback_window_days = Column(Integer, nullable=True)
    view_through_lookback_window_days = Column(Integer, nullable=True)
    include_in_conversions_metric = Column(Boolean, default=True)

    # Aggregated metrics (from last sync)
    conversions = Column(Float, default=0.0)
    all_conversions = Column(Float, default=0.0)
    conversion_value_micros = Column(BigInteger, default=0)

    __table_args__ = (
        UniqueConstraint("client_id", "google_conversion_action_id", name="uq_conversion_action_google_id"),
    )

    client = relationship("Client", back_populates="conversion_actions")
