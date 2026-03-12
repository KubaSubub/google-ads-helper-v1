"""SearchTerm model."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, BigInteger, Float, String, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class SearchTerm(Base):
    __tablename__ = "search_terms"

    id = Column(Integer, primary_key=True, index=True)
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=True)
    text = Column(String(1000), nullable=False)
    keyword_text = Column(String(500))  # The keyword that matched
    match_type = Column(String(20))
    segment = Column(String(20))  # IRRELEVANT, HIGH_PERFORMER, WASTE, OTHER
    source = Column(String(20), default="SEARCH")  # SEARCH or PMAX

    # â”€â”€ Core metrics â”€â”€
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)
    conversions = Column(Float, default=0.0)  # Float â€” Google Ads returns fractional values
    conversion_value_micros = Column(BigInteger, default=0)  # Revenue in micros
    ctr = Column(Integer, default=0)  # Stored as micros (e.g., 50000 = 5%)
    conversion_rate = Column(Integer, default=0)  # Stored as micros

    # â”€â”€ Extended Conversions â”€â”€
    all_conversions = Column(Float, nullable=True)
    all_conversions_value_micros = Column(BigInteger, nullable=True)
    cross_device_conversions = Column(Float, nullable=True)
    value_per_conversion_micros = Column(BigInteger, nullable=True)
    conversions_value_per_cost = Column(Float, nullable=True)  # Google's ROAS

    # Date range this data covers
    date_from = Column(Date, nullable=False)
    date_to = Column(Date, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    __table_args__ = (
        Index("idx_search_terms_cost", "cost_micros"),
        Index("idx_search_terms_date", "date_from", "date_to"),
        Index("idx_search_terms_text", "text"),
    )

    # Relationships
    ad_group = relationship("AdGroup", back_populates="search_terms")
    campaign = relationship("Campaign", back_populates="search_terms")

