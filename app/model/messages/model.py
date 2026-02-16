from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from ...db import Base


class Messages(Base):
    __tablename__ = "messages"

    message_id = Column(Integer, primary_key=True, autoincrement=True)

    client_id = Column(
        Integer,
        ForeignKey("client.client_id", ondelete="CASCADE"),
        nullable=True
    )

    text_message = Column(String(10000), nullable=True)
    response = Column(String(10000), nullable=True)

    # relationships
    client = relationship("Client", back_populates="messages")
