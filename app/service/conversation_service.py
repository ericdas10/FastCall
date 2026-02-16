# app/services/conversation_service.py

from app.persistence.unit_of_work import UnitOfWork
from .exceptions import NotFound, NotAllowed


class ConversationService:

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def list_client_messages(self, *, call_center_id: int, client_id: int):

        client = self.uow.clients.get(client_id)
        if not client:
            raise NotFound("Client not found")

        if client.call_center_id != call_center_id:
            raise NotAllowed("Client does not belong to this call center")

        return self.uow.messages.list_by_client(client_id)