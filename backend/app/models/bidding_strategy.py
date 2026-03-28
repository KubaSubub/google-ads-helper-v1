"""Bidding Strategy model — portfolio bid strategies and shared budgets."""

from sqlalchemy import Column, Integer, BigInteger, Float, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class BiddingStrategy(Base):
    __tablename__ = "bidding_strategies"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    google_strategy_id = Column(String(50), nullable=False)
    resource_name = Column(String(200), nullable=True)

    name = Column(String(200), nullable=False)
    strategy_type = Column(String(50), nullable=True)  # TARGET_CPA, TARGET_ROAS, MAXIMIZE_CONVERSIONS, etc.
    status = Column(String(20), default="ENABLED")

    # Strategy-specific settings
    target_cpa_micros = Column(BigInteger, nullable=True)
    target_roas = Column(Float, nullable=True)
    max_cpc_bid_ceiling_micros = Column(BigInteger, nullable=True)
    max_cpc_bid_floor_micros = Column(BigInteger, nullable=True)

    # Campaign count
    campaign_count = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("client_id", "google_strategy_id", name="uq_bidding_strategy"),
    )

    client = relationship("Client")


class SharedBudget(Base):
    __tablename__ = "shared_budgets"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    google_budget_id = Column(String(50), nullable=False)
    resource_name = Column(String(200), nullable=True)

    name = Column(String(200), nullable=False)
    amount_micros = Column(BigInteger, default=0)
    delivery_method = Column(String(20), nullable=True)  # STANDARD, ACCELERATED
    status = Column(String(20), default="ENABLED")
    campaign_count = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("client_id", "google_budget_id", name="uq_shared_budget"),
    )

    client = relationship("Client")
