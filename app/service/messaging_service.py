# app/services/messaging_service.py

from app.persistence.unit_of_work import UnitOfWork
from app.model.messages.model import Messages
from .exceptions import ValidationError, NotFound


class MessagingService:

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    def send_message(self, *, client_id: int, text: str):

        if not text or not text.strip():
            raise ValidationError("Message cannot be empty")

        client = self.uow.clients.get(client_id)
        if not client:
            raise NotFound("Client not found")

        msg = Messages(
            client_id=client_id,
            text_message=text.strip(),
            response="Ok"
        )

        self.uow.messages.add(msg)
        self.uow.messages.flush()
        self.uow.commit()

        return msg
