"""SearchTerm model."""

from datetime import datetime
from sqlalchemy import Column, Integer, BigInteger, String, Date, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class SearchTerm(Base):
    __tablename__ = "search_terms"

    id = Column(Integer, primary_key=True, index=True)
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=False)
    text = Column(String(1000), nullable=False)
    keyword_text = Column(String(500))  # The keyword that matched
    match_type = Column(String(20))

    # Metrics
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)
    conversions = Column(Integer, default=0)
    ctr = Column(Integer, default=0)  # Stored as micros (e.g., 50000 = 5%)
    conversion_rate = Column(Integer, default=0)  # Stored as micros

    # Date range this data covers
    date_from = Column(Date, nullable=False)
    date_to = Column(Date, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_search_terms_cost", "cost_micros"),
        Index("idx_search_terms_date", "date_from", "date_to"),
        Index("idx_search_terms_text", "text"),
    )

    # Relationships
    ad_group = relationship("AdGroup", back_populates="search_terms")
