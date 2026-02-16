from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum as SAEnum

from ...db import Base
from ..enums import CountryEnum, DomainEnum


class CallCenters(Base):
    __tablename__ = "call_centers"

    call_center_id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False)
    password = Column(String(100), nullable=False)  # va fi hash în practică
    email = Column(String(100), nullable=False)

    domain = Column(
        SAEnum(DomainEnum, native_enum=False, create_constraint=True),
        nullable=False
    )
    country = Column(
        SAEnum(CountryEnum, native_enum=False, create_constraint=True),
        nullable=False
    )

    number = Column(String(100), nullable=False)

    # relationships
    clients = relationship("Client", back_populates="call_center", cascade="all, delete-orphan")
