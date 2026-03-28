"""Models for negative keyword lists and their items."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class NegativeKeywordList(Base):
    __tablename__ = "negative_keyword_lists"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    google_shared_set_id = Column(BigInteger, nullable=True, index=True)
    google_resource_name = Column(String(300), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    source = Column(String(30), default="LOCAL")  # LOCAL | GOOGLE_ADS_SYNC
    member_count = Column(Integer, default=0)
    status = Column(String(20), default="ENABLED")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    client = relationship("Client")
    items = relationship("NegativeKeywordListItem", back_populates="keyword_list", cascade="all, delete-orphan")


class NegativeKeywordListItem(Base):
    __tablename__ = "negative_keyword_list_items"

    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(Integer, ForeignKey("negative_keyword_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    google_criterion_id = Column(BigInteger, nullable=True)
    text = Column(String(500), nullable=False)
    match_type = Column(String(20), default="PHRASE")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    keyword_list = relationship("NegativeKeywordList", back_populates="items")

    __table_args__ = (UniqueConstraint("list_id", "text", "match_type", name="uq_list_text_match"),)
