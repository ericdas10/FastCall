from typing import Optional
from sqlalchemy.orm import Session
from app.model.revoked_tokens.model import RevokedTokens
from .base import BaseRepository

class RevokedTokensRepository(BaseRepository[RevokedTokens]):
    def __init__(self, session: Session):
        super().__init__(session, RevokedTokens)

    def is_revoked(self, jti: str) -> bool:
        return self.session.query(self.model).filter(self.model.jti == jti).count() > 0

    def revoke(self, jti: str) -> RevokedTokens:
        entity = RevokedTokens(jti=jti)
        self.add(entity)
        return entity