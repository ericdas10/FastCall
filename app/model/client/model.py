from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum as SAEnum

from ...db import Base
from ..enums import CountryEnum


class Client(Base):
    __tablename__ = "client"

    client_id = Column(Integer, primary_key=True, autoincrement=True)

    call_center_id = Column(
        Integer,
        ForeignKey("call_centers.call_center_id", ondelete="CASCADE"),
        nullable=True
    )

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False)
    password = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)

    country = Column(
        SAEnum(CountryEnum, native_enum=False, create_constraint=True),
        nullable=False
    )

    number = Column(String(100), nullable=False)

    # relationships
    call_center = relationship("CallCenters", back_populates="clients")
    messages = relationship("Messages", back_populates="client", cascade="all, delete-orphan")
