from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON
from sqlalchemy.orm import relationship

from ...db import Base


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(Integer, primary_key=True, autoincrement=True)

    client_id = Column(
        Integer,
        ForeignKey("client.client_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    call_center_id = Column(
        Integer,
        ForeignKey("call_centers.call_center_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # "success" | "failure"
    status = Column(String(20), nullable=False)

    # Full conversation snapshot (list of {role, content, ts}) + summary, slots, etc.
    payload = Column(JSON, nullable=False)

    summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    client = relationship("Client", back_populates="tickets")
    call_center = relationship("CallCenters", back_populates="tickets")
