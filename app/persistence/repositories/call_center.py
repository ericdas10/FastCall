# app/persistence/repositories/call_centers.py
from typing import Protocol, Optional, List
from sqlalchemy.orm import Session
from app.model.call_centers.model import CallCenters
from .base import BaseRepository

class ICallCentersRepository(Protocol):
    def add(self, entity: CallCenters) -> CallCenters: ...
    def get(self, pk: int) -> Optional[CallCenters]: ...
    def get_by_email(self, email: str) -> Optional[CallCenters]: ...
    def list_all(self) -> List[CallCenters]: ...

class CallCentersRepository(BaseRepository[CallCenters]):
    def __init__(self, session: Session):
        super().__init__(session, CallCenters)

    def get_by_email(self, email: str) -> Optional[CallCenters]:
        return self.session.query(self.model).filter(self.model.email == email).one_or_none()