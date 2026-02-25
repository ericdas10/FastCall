from app.persistence.unit_of_work import UnitOfWork
from app.model.messages.model import Messages
from .exceptions import ValidationError, NotFound
from ..rag.pipeline import RagPipeline


class MessagingService:

    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.rag = RagPipeline()

    def send_message(self, *, client_id: int, text: str):

        if not text or not text.strip():
            raise ValidationError("Message cannot be empty")

        client = self.uow.clients.get(client_id)
        if not client:
            raise NotFound("Client not found")

        answer = self.rag.answer(
            call_center_id=client.call_center_id,
            session_id=str(client_id),
            question=text.strip()
        )

        msg = Messages(
            client_id=client_id,
            text_message=text.strip(),
            response=answer
        )

        self.uow.messages.add(msg)
        self.uow.messages.flush()
        self.uow.commit()

        return msg