from fastapi import APIRouter, Depends, HTTPException
from app.persistence.unit_of_work import get_uow, UnitOfWork
from app.service.conversation_service import ConversationService
from app.service.exceptions import NotFound, NotAllowed
from app.security.current_actor import get_current_actor, CurrentActor

router = APIRouter(prefix="/messages", tags=["messages"])

@router.get("/me/conversation")
def get_my_conversation(actor: CurrentActor = Depends(get_current_actor), uow: UnitOfWork = Depends(get_uow)):
    """
    Only clients can get their own conversation history.
    """
    if actor.actor_type != "client":
        raise HTTPException(status_code=403, detail="Only clients can access their conversation")

    svc = ConversationService(uow)
    try:
        messages = svc.list_client_messages(call_center_id=actor.call_center_id, client_id=actor.actor_id)
        conversation = []
        
        for m in messages:
            # Add user message
            if m.text_message:
                conversation.append({
                    "message_id": m.message_id,
                    "content": m.text_message,
                    "sender_type": "user",
                    "timestamp": m.timestamp.isoformat() if hasattr(m, 'timestamp') and m.timestamp else None
                })
            
            # Add AI response
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
