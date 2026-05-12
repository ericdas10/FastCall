from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.persistence.unit_of_work import get_uow, UnitOfWork
from app.security.current_actor import get_current_actor, CurrentActor
from app.service.conversation_service import ConversationService
from app.service.exceptions import NotFound, NotAllowed, ValidationError


router = APIRouter(prefix="/conversations", tags=["conversations"])


class SendMessageBody(BaseModel):
    text: str


class CloseBody(BaseModel):
    success: bool


def _require_client(actor: CurrentActor):
    if actor.actor_type != "client":
        raise HTTPException(status_code=403, detail="Only clients can manage conversations")


@router.post("", status_code=201)
def create_conversation(
    actor: CurrentActor = Depends(get_current_actor),
    uow: UnitOfWork = Depends(get_uow),
):
    _require_client(actor)
    svc = ConversationService(uow)
    try:
        conv_id = svc.create_conversation(client_id=actor.actor_id)
        return {"conversation_id": conv_id, "turns": []}
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/open")
def list_open_conversations(
    actor: CurrentActor = Depends(get_current_actor),
    uow: UnitOfWork = Depends(get_uow),
):
    _require_client(actor)
    svc = ConversationService(uow)
    try:
        return svc.list_open_conversations(client_id=actor.actor_id)
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: str,
    actor: CurrentActor = Depends(get_current_actor),
    uow: UnitOfWork = Depends(get_uow),
):
    _require_client(actor)
    svc = ConversationService(uow)
    try:
        return svc.get_open_conversation(
            client_id=actor.actor_id, conversation_id=conversation_id
        )
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{conversation_id}/messages")
def send_message(
    conversation_id: str,
    body: SendMessageBody,
    actor: CurrentActor = Depends(get_current_actor),
    uow: UnitOfWork = Depends(get_uow),
):
    _require_client(actor)
    svc = ConversationService(uow)
    try:
        return svc.send_message(
            client_id=actor.actor_id,
            conversation_id=conversation_id,
            text=body.text,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{conversation_id}/close")
def close_conversation(
    conversation_id: str,
    body: CloseBody,
    actor: CurrentActor = Depends(get_current_actor),
    uow: UnitOfWork = Depends(get_uow),
):
    _require_client(actor)
    svc = ConversationService(uow)
    try:
        ticket = svc.close_conversation(
            client_id=actor.actor_id,
            conversation_id=conversation_id,
            success=body.success,
        )
        return {
            "ticket_id": ticket.ticket_id,
            "status": ticket.status,
            "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        }
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------- Tickets ----------

tickets_router = APIRouter(prefix="/tickets", tags=["tickets"])


@tickets_router.get("/me")
def list_my_tickets(
    actor: CurrentActor = Depends(get_current_actor),
    uow: UnitOfWork = Depends(get_uow),
):
    _require_client(actor)
    svc = ConversationService(uow)
    try:
        tickets = svc.list_client_tickets(client_id=actor.actor_id)
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return [
        {
            "ticket_id": t.ticket_id,
            "status": t.status,
            "summary": t.summary,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            "preview": _ticket_preview(t),
        }
        for t in tickets
    ]


@tickets_router.get("/me/{ticket_id}")
def get_my_ticket(
    ticket_id: int,
    actor: CurrentActor = Depends(get_current_actor),
    uow: UnitOfWork = Depends(get_uow),
):
    _require_client(actor)
    svc = ConversationService(uow)
    try:
        t = svc.get_client_ticket(client_id=actor.actor_id, ticket_id=ticket_id)
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {
        "ticket_id": t.ticket_id,
        "status": t.status,
        "summary": t.summary,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "closed_at": t.closed_at.isoformat() if t.closed_at else None,
        "payload": t.payload,
    }


def _ticket_preview(t) -> str:
    try:
        for turn in (t.payload or {}).get("turns", []):
            if turn.get("role") == "user":
                content = turn.get("content") or ""
                return content[:140]
    except Exception:
        pass
    return ""
