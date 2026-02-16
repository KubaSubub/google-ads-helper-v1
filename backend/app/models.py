"""SQLAlchemy ORM models for the Google Ads Helper App.

Schema hierarchy:
  Client → Campaign → AdGroup → Keyword
                              → SearchTerm
                              → Ad
  Client → AutomatedRule → ExecutionQueueItem
  Campaign → MetricDaily
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, Date, DateTime,
    ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.database import Base


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    google_customer_id = Column(String(20), unique=True, nullable=False)
    industry = Column(String(100))
    website = Column(String(500))
    target_audience = Column(Text)
    usp = Column(Text)  # Unique Selling Proposition
    competitors = Column(JSON, default=list)  # ["competitor1.pl", ...]
    seasonality = Column(JSON, default=list)  # [{period, multiplier}, ...]
    business_rules = Column(JSON, default=dict)  # {min_roas, max_daily_budget, ...}
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaigns = relationship("Campaign", back_populates="client", cascade="all, delete-orphan")
    automated_rules = relationship("AutomatedRule", back_populates="client", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    google_campaign_id = Column(String(50), nullable=False)
    name = Column(String(500), nullable=False)
    status = Column(String(20))  # ENABLED, PAUSED, REMOVED
    campaign_type = Column(String(50))  # SEARCH, DISPLAY, SHOPPING, etc.
    budget_amount = Column(Float)
    budget_type = Column(String(20))  # DAILY, TOTAL
    bidding_strategy = Column(String(50))
    start_date = Column(Date)
    end_date = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("client_id", "google_campaign_id", name="uq_campaign_google_id"),
    )

    # Relationships
    client = relationship("Client", back_populates="campaigns")
    ad_groups = relationship("AdGroup", back_populates="campaign", cascade="all, delete-orphan")
    metrics_daily = relationship("MetricDaily", back_populates="campaign", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Ad Group
# ---------------------------------------------------------------------------

class AdGroup(Base):
    __tablename__ = "ad_groups"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    google_ad_group_id = Column(String(50), nullable=False)
    name = Column(String(500), nullable=False)
    status = Column(String(20))  # ENABLED, PAUSED, REMOVED
    cpc_bid = Column(Float)  # Max CPC bid in micros
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("campaign_id", "google_ad_group_id", name="uq_ad_group_google_id"),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="ad_groups")
    keywords = relationship("Keyword", back_populates="ad_group", cascade="all, delete-orphan")
    search_terms = relationship("SearchTerm", back_populates="ad_group", cascade="all, delete-orphan")
    ads = relationship("Ad", back_populates="ad_group", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Keyword
# ---------------------------------------------------------------------------

class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=False)
    google_keyword_id = Column(String(50))
    text = Column(String(500), nullable=False)
    match_type = Column(String(20))  # EXACT, PHRASE, BROAD
    status = Column(String(20))  # ENABLED, PAUSED, REMOVED
    final_url = Column(String(2000))
    cpc_bid = Column(Float)

    # Aggregated metrics (latest sync period)
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    conversions = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)
    avg_cpc = Column(Float, default=0.0)
    quality_score = Column(Integer, default=0)  # Google Ads Quality Score 1-10

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ad_group = relationship("AdGroup", back_populates="keywords")


# ---------------------------------------------------------------------------
# Search Term
# ---------------------------------------------------------------------------

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
    cost = Column(Float, default=0.0)
    conversions = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)
    conversion_rate = Column(Float, default=0.0)
    cost_per_conversion = Column(Float, default=0.0)

    # Date range this data covers
    date_from = Column(Date, nullable=False)
    date_to = Column(Date, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_search_terms_cost", "cost"),
        Index("idx_search_terms_date", "date_from", "date_to"),
        Index("idx_search_terms_text", "text"),
    )

    # Relationships
    ad_group = relationship("AdGroup", back_populates="search_terms")


# ---------------------------------------------------------------------------
# Ad
# ---------------------------------------------------------------------------

class Ad(Base):
    __tablename__ = "ads"

    id = Column(Integer, primary_key=True, index=True)
    ad_group_id = Column(Integer, ForeignKey("ad_groups.id", ondelete="CASCADE"), nullable=False)
    google_ad_id = Column(String(50))
    ad_type = Column(String(50))  # RESPONSIVE_SEARCH_AD, etc.
    status = Column(String(20))
    final_url = Column(String(2000))

    # RSA components stored as JSON arrays
    headlines = Column(JSON, default=list)  # [{"text": "...", "pinned_position": null}, ...]
    descriptions = Column(JSON, default=list)

    # Metrics
    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    conversions = Column(Float, default=0.0)
    ctr = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ad_group = relationship("AdGroup", back_populates="ads")

    @property
    def headline_1(self):
        """First headline from RSA headlines JSON."""
        if self.headlines and len(self.headlines) > 0:
            h = self.headlines[0]
            return h.get("text", h) if isinstance(h, dict) else str(h)
        return None

    @property
    def headline_2(self):
        """Second headline from RSA headlines JSON."""
        if self.headlines and len(self.headlines) > 1:
            h = self.headlines[1]
            return h.get("text", h) if isinstance(h, dict) else str(h)
        return None


# ---------------------------------------------------------------------------
# Daily Metrics (Time-series data for campaigns)
# ---------------------------------------------------------------------------

class MetricDaily(Base):
    __tablename__ = "metrics_daily"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)

    clicks = Column(Integer, default=0)
    impressions = Column(Integer, default=0)
    ctr = Column(Float, default=0.0)
    conversions = Column(Float, default=0.0)
    conversion_rate = Column(Float, default=0.0)
    cost = Column(Float, default=0.0)
    cost_per_conversion = Column(Float, default=0.0)
    roas = Column(Float, default=0.0)
    avg_cpc = Column(Float, default=0.0)

    __table_args__ = (
        UniqueConstraint("campaign_id", "date", name="uq_metric_daily"),
        Index("idx_metrics_daily_date", "date"),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="metrics_daily")


# ---------------------------------------------------------------------------
# Automated Rules
# ---------------------------------------------------------------------------

class AutomatedRule(Base):
    __tablename__ = "automated_rules"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    conditions = Column(JSON, nullable=False)  # {all: [{metric, operator, value}, ...]}
    actions = Column(JSON, nullable=False)  # [{type, params}, ...]
    entity_type = Column(String(20), default="keyword")  # keyword, search_term, campaign
    frequency = Column(String(20), default="weekly")  # hourly, daily, weekly, manual
    require_approval = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="automated_rules")
    execution_items = relationship("ExecutionQueueItem", back_populates="rule", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Execution Queue
# ---------------------------------------------------------------------------

class ExecutionQueueItem(Base):
    __tablename__ = "execution_queue"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("automated_rules.id", ondelete="CASCADE"), nullable=False)
    action_type = Column(String(50), nullable=False)  # pause_keyword, adjust_bid, add_negative_keyword, etc.
    target_entity_type = Column(String(20))  # keyword, campaign, ad_group
    target_entity_id = Column(String(50))
    params = Column(JSON, default=dict)
    status = Column(String(20), default="pending")  # pending, approved, executed, failed, cancelled
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime)

    __table_args__ = (
        Index("idx_execution_queue_status", "status"),
    )

    # Relationships
    rule = relationship("AutomatedRule", back_populates="execution_items")


# ---------------------------------------------------------------------------
# Access Log (RODO compliance)
# ---------------------------------------------------------------------------

class AccessLog(Base):
    __tablename__ = "access_log"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(50), nullable=False)  # view, create, update, delete, execute
    resource_type = Column(String(50))  # client, campaign, keyword, rule
    resource_id = Column(Integer)
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
