import uuid
from datetime import datetime
from typing import Dict, List, Tuple

from app.persistence.unit_of_work import UnitOfWork
from app.model.tickets.model import Ticket
from app.agent.registry import get_operator
from app.agent.memory import get_memory
from app.agent.tools.faq_tool import FaqStore
from app.agent.faq_extractor import extract_faq_from_ticket
from .exceptions import NotFound, NotAllowed, ValidationError


# In-process registry of OPEN conversations per client.
# Maps client_id -> list of conversation_ids the client owns. The actual chat
# state (turns, summary, slots) lives inside the agent's AgentMemory cache.
_open_conversations: Dict[int, List[str]] = {}


def _make_session_id() -> str:
    return uuid.uuid4().hex


class ConversationService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.memory = get_memory()

    # ---------- Client side ----------

    def _require_client(self, client_id: int):
        client = self.uow.clients.get(client_id)
        if not client:
            raise NotFound("Client not found")
        return client

    def create_conversation(self, *, client_id: int) -> str:
        client = self._require_client(client_id)
        conv_id = _make_session_id()
        # Pre-create the in-memory state so it shows up immediately.
        self.memory.get(client.call_center_id, conv_id)
        _open_conversations.setdefault(client_id, []).append(conv_id)
        return conv_id

    def _ensure_open(self, client_id: int, conversation_id: str) -> int:
        """Returns call_center_id for the conversation."""
        client = self._require_client(client_id)
        ids = _open_conversations.get(client_id, [])
        if conversation_id not in ids:
            raise NotFound("Conversation not found or already closed")
        return client.call_center_id

    def send_message(self, *, client_id: int, conversation_id: str, text: str) -> dict:
        if not text or not text.strip():
            raise ValidationError("Message cannot be empty")

        call_center_id = self._ensure_open(client_id, conversation_id)

        operator = get_operator(call_center_id)
        state = self.memory.get(call_center_id, conversation_id)
        result = operator.answer(state=state, question=text.strip())
        return {
            "answer": result["answer"],
            "conversation_finished": result["conversation_finished"],
        }

    def list_open_conversations(self, *, client_id: int) -> list:
        client = self._require_client(client_id)
        out = []
        for conv_id in list(_open_conversations.get(client_id, [])):
            state = self.memory.get(client.call_center_id, conv_id)
            turns = [
                {"role": t.role, "content": t.content, "ts": t.ts}
                for t in state.turns
            ]
            preview = next((t["content"] for t in turns if t["role"] == "user"), "")
            out.append(
                {
                    "conversation_id": conv_id,
                    "turns": turns,
                    "preview": preview,
                    "summary": state.summary,
                }
            )
        return out

    def get_open_conversation(self, *, client_id: int, conversation_id: str) -> dict:
        call_center_id = self._ensure_open(client_id, conversation_id)
        state = self.memory.get(call_center_id, conversation_id)
        return {
            "conversation_id": conversation_id,
            "turns": [
                {"role": t.role, "content": t.content, "ts": t.ts}
                for t in state.turns
            ],
            "summary": state.summary,
        }

    def close_conversation(
        self, *, client_id: int, conversation_id: str, success: bool
    ) -> Ticket:
        client = self._require_client(client_id)
        ids = _open_conversations.get(client_id, [])
        if conversation_id not in ids:
            raise NotFound("Conversation not found or already closed")

        state = self.memory.get(client.call_center_id, conversation_id)

        payload = {
            "conversation_id": conversation_id,
            "client_id": client_id,
            "call_center_id": client.call_center_id,
            "status": "success" if success else "failure",
            "turns": [
                {"role": t.role, "content": t.content, "ts": t.ts}
                for t in state.turns
            ],
            "summary": state.summary,
            "slots": state.slots,
            "closed_at": datetime.utcnow().isoformat(),
        }

        ticket = Ticket(
            client_id=client_id,
            call_center_id=client.call_center_id,
            status="success" if success else "failure",
            payload=payload,
            summary=state.summary or None,
            created_at=datetime.utcnow(),
            closed_at=datetime.utcnow(),
        )
        self.uow.tickets.add(ticket)
        self.uow.tickets.flush()
        self.uow.commit()

        # If the conversation was a success, mine generic Q/A into the FAQ.
        if success:
            try:
                faq_store = FaqStore(call_center_id=client.call_center_id)
                extract_faq_from_ticket(payload, faq_store)
            except Exception:
                # FAQ extraction is best-effort; never fail the close because of it.
                pass

        # Clear in-memory state and registry entry
        self.memory.reset(client.call_center_id, conversation_id)
        ids.remove(conversation_id)
        if not ids:
            _open_conversations.pop(client_id, None)

        return ticket

    # ---------- Tickets (history) ----------

    def list_client_tickets(self, *, client_id: int) -> List[Ticket]:
        self._require_client(client_id)
        return self.uow.tickets.list_by_client(client_id)

    def get_client_ticket(self, *, client_id: int, ticket_id: int) -> Ticket:
        ticket = self.uow.tickets.get_for_client(ticket_id, client_id)
        if not ticket:
            raise NotFound("Ticket not found")
        return ticket

    # ---------- Call center side ----------

    def list_clients_for_call_center(self, *, call_center_id: int):
        return self.uow.clients.list_by_call_center(call_center_id)

    def call_center_dashboard(self, *, call_center_id: int) -> List[dict]:
        clients = self.uow.clients.list_by_call_center(call_center_id)
        counts = self.uow.tickets.counts_per_client(call_center_id)

        out = []
        total_success = 0
        total_failure = 0
        for c in clients:
            entry = counts.get(c.client_id, {"success": 0, "failure": 0, "total": 0})
            total_success += entry["success"]
            total_failure += entry["failure"]
            out.append(
                {
                    "client_id": c.client_id,
                    "first_name": c.first_name,
                    "last_name": c.last_name,
                    "email": c.email,
                    "username": c.username,
                    "success_count": entry["success"],
                    "failure_count": entry["failure"],
                    "total_count": entry["total"],
                }
            )
        return out
