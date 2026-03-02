"""KeywordDaily model — per-keyword per-day metrics for time-series analysis."""

from sqlalchemy import Column, Integer, BigInteger, Float, Date, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from app.database import Base


class KeywordDaily(Base):
    __tablename__ = "keywords_daily"

    id = Column(Integer, primary_key=True, index=True)
    keyword_id = Column(Integer, ForeignKey("keywords.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    # Core summable metrics
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost_micros = Column(BigInteger, default=0)
    conversions = Column(Float, default=0.0)
    conversion_value_micros = Column(BigInteger, default=0)
    avg_cpc_micros = Column(BigInteger, default=0)

    __table_args__ = (
        UniqueConstraint("keyword_id", "date", name="uq_keyword_daily"),
        Index("idx_keywords_daily_date", "date"),
        Index("idx_keywords_daily_keyword", "keyword_id"),
    )

    keyword = relationship("Keyword", back_populates="metrics_daily")
