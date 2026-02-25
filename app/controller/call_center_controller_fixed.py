from fastapi import APIRouter, Depends, HTTPException
from app.persistence.unit_of_work import get_uow, UnitOfWork
from app.service.conversation_service import ConversationService
from app.service.exceptions import NotFound, NotAllowed
from app.security.current_actor import get_current_actor, CurrentActor

router = APIRouter(prefix="/call-centers", tags=["call-centers"])

@router.get("/me/clients")
def list_my_clients(actor: CurrentActor = Depends(get_current_actor), uow: UnitOfWork = Depends(get_uow)):
    if actor.actor_type != "call_center":
        raise HTTPException(status_code=403, detail="Only call centers can access this")

    svc = ConversationService(uow)
    clients = svc.list_clients_for_call_center(call_center_id=actor.actor_id)

    return [
        {
            "client_id": c.client_id,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "email": c.email,
            "username": c.username
        }
        for c in clients
    ]

@router.get("/me/clients/{client_id}/messages")
def list_client_messages(client_id: int, actor: CurrentActor = Depends(get_current_actor), uow: UnitOfWork = Depends(get_uow)):
    if actor.actor_type != "call_center":
        raise HTTPException(status_code=403, detail="Only call centers can access this")

    svc = ConversationService(uow)
    try:
        messages = svc.list_client_messages(call_center_id=actor.actor_id, client_id=client_id)
        conversation = []
        
        for m in messages:
            if m.text_message:
                conversation.append({
                    "message_id": m.message_id,
                    "content": m.text_message,
                    "sender_type": "user",
                    "timestamp": m.timestamp.isoformat() if hasattr(m, 'timestamp') and m.timestamp else None
                })
            
            if m.response:
                conversation.append({
                    "message_id": m.message_id,
                    "content": m.response,
                    "sender_type": "ai",
                    "timestamp": m.timestamp.isoformat() if hasattr(m, 'timestamp') and m.timestamp else None
                })
        
        return conversation
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except NotAllowed as e:
        raise HTTPException(status_code=403, detail=str(e))
