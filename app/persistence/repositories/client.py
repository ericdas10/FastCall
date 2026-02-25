from typing import Protocol, Optional, List
from sqlalchemy.orm import Session
from app.model.client.model import Client
from .base import BaseRepository

class IClientRepository(Protocol):
    def add(self, entity: Client) -> Client: ...
    def get(self, pk: int) -> Optional[Client]: ...
    def get_by_email(self, email: str) -> Optional[Client]: ...
    def list_by_call_center(self, call_center_id: int) -> List[Client]: ...

class ClientRepository(BaseRepository[Client]):
    def __init__(self, session: Session):
        super().__init__(session, Client)

    def get_by_email(self, email: str) -> Optional[Client]:
        return self.session.query(self.model).filter(self.model.email == email).one_or_none()

    def list_by_call_center(self, call_center_id: int):
        return self.session.query(self.model).filter(self.model.call_center_id == call_center_id).all()