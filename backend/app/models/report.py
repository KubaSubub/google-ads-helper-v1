"""Report model for persisting generated monthly/periodic reports."""

from datetime import datetime

from sqlalchemy import Column, Integer, Float, String, Text, Date, DateTime, ForeignKey, Index
from app.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    report_type = Column(String(50), nullable=False, default="monthly")
    period_label = Column(String(20), nullable=True)  # e.g. "2026-03"
    date_from = Column(Date, nullable=True)
    date_to = Column(Date, nullable=True)
    status = Column(String(20), nullable=False, default="generating")
    report_data = Column(Text, nullable=True)  # JSON blob of structural data
    ai_narrative = Column(Text, nullable=True)  # Claude markdown output
    error_message = Column(Text, nullable=True)
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    cache_read_tokens = Column(Integer, nullable=True)
    total_cost_usd = Column(Float, nullable=True)
    model_name = Column(String(100), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_reports_client_id", "client_id"),
        Index("ix_reports_created_at", "created_at"),
    )
