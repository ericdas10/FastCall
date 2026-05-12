from typing import Optional, List
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.model.tickets.model import Ticket
from .base import BaseRepository


class TicketsRepository(BaseRepository[Ticket]):
    def __init__(self, session: Session):
        super().__init__(session, Ticket)

    def list_by_client(self, client_id: int) -> List[Ticket]:
        return (
            self.session.query(self.model)
            .filter(self.model.client_id == client_id)
            .order_by(self.model.created_at.desc())
            .all()
        )

    def get_for_client(self, ticket_id: int, client_id: int) -> Optional[Ticket]:
        return (
            self.session.query(self.model)
            .filter(self.model.ticket_id == ticket_id, self.model.client_id == client_id)
            .one_or_none()
        )

    def stats_for_call_center(self, call_center_id: int):
        """Return list of (client_id, success_count, failure_count, total)."""
        rows = (
            self.session.query(
                self.model.client_id,
                func.sum(
                    (self.model.status == "success").cast_to_int()
                    if hasattr(self.model.status, "cast_to_int")
                    else func.cast(self.model.status == "success", type_=None)
                ),
            )
            .filter(self.model.call_center_id == call_center_id)
            .group_by(self.model.client_id)
            .all()
        )
        return rows

    def counts_per_client(self, call_center_id: int):
        """
        Returns dict: {client_id: {"success": n, "failure": m, "total": n+m}}
        """
        rows = (
            self.session.query(self.model.client_id, self.model.status, func.count())
            .filter(self.model.call_center_id == call_center_id)
            .group_by(self.model.client_id, self.model.status)
            .all()
        )
        out: dict = {}
        for client_id, status, cnt in rows:
            entry = out.setdefault(client_id, {"success": 0, "failure": 0, "total": 0})
            if status == "success":
                entry["success"] = int(cnt)
            elif status == "failure":
                entry["failure"] = int(cnt)
            entry["total"] = entry["success"] + entry["failure"]
        return out
