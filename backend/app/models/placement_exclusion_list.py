"""Models for MCC-level placement exclusion lists and their items."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class PlacementExclusionList(Base):
    __tablename__ = "placement_exclusion_lists"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    google_shared_set_id = Column(BigInteger, nullable=True, index=True)
    google_resource_name = Column(String(300), nullable=True)
    name = Column(String(200), nullable=False)
    description = Column(String(500), nullable=True)
    source = Column(String(30), default="LOCAL")  # LOCAL | GOOGLE_ADS_SYNC | MCC_SYNC
    ownership_level = Column(String(10), default="account")  # mcc | account
    member_count = Column(Integer, default=0)
    status = Column(String(20), default="ENABLED")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    client = relationship("Client")
    items = relationship("PlacementExclusionListItem", back_populates="exclusion_list", cascade="all, delete-orphan")


class PlacementExclusionListItem(Base):
    __tablename__ = "placement_exclusion_list_items"

    id = Column(Integer, primary_key=True, index=True)
    list_id = Column(Integer, ForeignKey("placement_exclusion_lists.id", ondelete="CASCADE"), nullable=False, index=True)
    google_criterion_id = Column(BigInteger, nullable=True)
    url = Column(String(2048), nullable=False)
    placement_type = Column(String(30), default="WEBSITE")  # WEBSITE | YOUTUBE_CHANNEL | YOUTUBE_VIDEO | MOBILE_APP
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    exclusion_list = relationship("PlacementExclusionList", back_populates="items")

    __table_args__ = (UniqueConstraint("list_id", "url", name="uq_placement_list_url"),)
