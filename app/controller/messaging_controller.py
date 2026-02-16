from fastapi import APIRouter, Depends, HTTPException, status
from app.persistence.unit_of_work import get_uow, UnitOfWork
from app.service.messaging_service import MessagingService
from app.service.exceptions import ValidationError, NotFound, NotAllowed
from app.schemas.message import SendMessageIn, SendMessageOut
from app.security.current_actor import get_current_actor, CurrentActor

router = APIRouter(prefix="/messages", tags=["messages"])

@router.post("", response_model=SendMessageOut, status_code=201)
def send_message(dto: SendMessageIn,
                 actor: CurrentActor = Depends(get_current_actor),
                 uow: UnitOfWork = Depends(get_uow)):
    """
    Only clients can send messages.
    """
    if actor.actor_type != "client":
        raise HTTPException(status_code=403, detail="Only clients can send messages")

    svc = MessagingService(uow)
    try:
        msg = svc.send_message(client_id=actor.actor_id, text=dto.text)
        return SendMessageOut(message_id=msg.message_id, response=msg.response or "Ok")
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NotFound as e:
        raise HTTPException(status_code=404, detail=str(e))