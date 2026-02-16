from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index
from ...db import Base

class RevokedTokens(Base):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jti = Column(String(128), nullable=False, unique=True)  # JWT ID
    revoked_at = Column(DateTime, default=datetime.utcnow, nullable=False)

Index("ix_revoked_tokens_jti", RevokedTokens.jti)