"""Bid simulator model — forecast curves from Google Ads.

Google Ads exposes `keyword_view.bid_simulator_points` (and for ad groups the
`ad_group.bid_simulator_points`) — a set of (bid_micros → clicks/impressions/cost/
conversions) tuples that answer "what happens if I change the bid?" locally,
without waiting days for the real learning.

Each row is one *point* on the curve. A single keyword/ad_group typically has
5-10 points covering the ±30% range around the current bid.

Columns follow the API shape (all forecasted metrics, not realised) plus the
context needed to join back to the keyword/ad_group:

    - entity: ('keyword', keyword_id) or ('ad_group', ad_group_id)
    - point index within curve (for ordering)
    - bid_micros at this point
    - forecasted clicks, impressions, cost_micros, biddable_conversions,
      biddable_conversions_value_micros, top_slot_impressions

Curves expire — Google recomputes them periodically. We store the `fetched_at`
timestamp and the `start_date`/`end_date` of the window the forecast applies to;
a daily sync overwrites yesterday's point set.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Column, Date, DateTime, Float, ForeignKey, Index, Integer, String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base


class BidSimulatorPoint(Base):
    __tablename__ = "bid_simulator_points"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)

    # Entity the point belongs to — either keyword or ad_group (exactly one set).
    entity_type = Column(String(20), nullable=False)  # "keyword" | "ad_group"
    keyword_id = Column(Integer, ForeignKey("keywords.id", ondelete="CASCADE"), nullable=True, index=True)
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=True, index=True)

    # Window the forecast applies to (Google reports it per request window).
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Point details
    point_index = Column(Integer, nullable=False)          # 0..N-1 in curve
    bid_micros = Column(BigInteger, nullable=False)

    # Forecasted metrics
    forecasted_clicks = Column(Integer, default=0)
    forecasted_impressions = Column(Integer, default=0)
    forecasted_cost_micros = Column(BigInteger, default=0)
    forecasted_conversions = Column(Float, default=0.0)
    forecasted_conversions_value_micros = Column(BigInteger, default=0)
    forecasted_top_slot_impressions = Column(Integer, default=0)

    fetched_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False,
    )

    __table_args__ = (
        # A keyword / ad_group has at most one point at a given bid level within a window.
        UniqueConstraint(
            "keyword_id", "ad_group_id", "start_date", "end_date", "bid_micros",
            name="uq_bid_simulator_point",
        ),
        Index("idx_bid_simulator_keyword", "keyword_id"),
        Index("idx_bid_simulator_ad_group", "ad_group_id"),
        Index("idx_bid_simulator_fetched_at", "fetched_at"),
    )

    keyword = relationship("Keyword")
    ad_group = relationship("AdGroup")
