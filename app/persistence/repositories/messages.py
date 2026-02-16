# app/persistence/repositories/messages.py
from typing import Protocol, Optional, List
from sqlalchemy.orm import Session
from app.model.messages.model import Messages
from .base import BaseRepository

class IMessagesRepository(Protocol):
    def add(self, entity: Messages) -> Messages: ...
    def get(self, pk: int) -> Optional[Messages]: ...
    def list_by_client(self, client_id: int) -> List[Messages]: ...

class MessagesRepository(BaseRepository[Messages]):
    def __init__(self, session: Session):
        super().__init__(session, Messages)

    def list_by_client(self, client_id: int):
        return self.session.query(self.model).filter(self.model.client_id == client_id).order_by(self.model.message_id).all()