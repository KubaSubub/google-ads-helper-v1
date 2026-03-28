"""MCC Link model — Manager account hierarchy."""

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class MccLink(Base):
    __tablename__ = "mcc_links"

    id = Column(Integer, primary_key=True, index=True)
    manager_customer_id = Column(String(20), nullable=False, index=True)
    client_customer_id = Column(String(20), nullable=False, index=True)
    client_descriptive_name = Column(String(500), nullable=True)
    status = Column(String(20), default="ENABLED")  # ENABLED, INVITED, PENDING, REFUSED
    is_hidden = Column(Boolean, default=False)
    is_manager = Column(Boolean, default=False)

    # Link to local client if exists
    local_client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        UniqueConstraint("manager_customer_id", "client_customer_id", name="uq_mcc_link"),
    )

    local_client = relationship("Client")
