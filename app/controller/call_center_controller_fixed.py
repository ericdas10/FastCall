from fastapi import APIRouter, Depends, HTTPException
from app.persistence.unit_of_work import get_uow, UnitOfWork
from app.service.conversation_service import ConversationService
from app.service.exceptions import NotFound, NotAllowed
from app.security.current_actor import get_current_actor, CurrentActor

router = APIRouter(prefix="/call-centers", tags=["call-centers"])


def _require_call_center(actor: CurrentActor):
    if actor.actor_type != "call_center":
        raise HTTPException(status_code=403, detail="Only call centers can access this")


@router.get("/me/clients")
def list_my_clients(actor: CurrentActor = Depends(get_current_actor), uow: UnitOfWork = Depends(get_uow)):
    _require_call_center(actor)

    svc = ConversationService(uow)
    clients = svc.list_clients_for_call_center(call_center_id=actor.actor_id)

    return [
        {
            "client_id": c.client_id,
            "first_name": c.first_name,
            "last_name": c.last_name,
            "email": c.email,
            "username": c.username,
        }
        for c in clients
    ]


@router.get("/me/dashboard")
def call_center_dashboard(
    actor: CurrentActor = Depends(get_current_actor),
    uow: UnitOfWork = Depends(get_uow),
):
    """
    Per-client ticket counts (success vs failure). The call center has NO access
    to the conversation contents anymore.
    """
    _require_call_center(actor)
    svc = ConversationService(uow)
    rows = svc.call_center_dashboard(call_center_id=actor.actor_id)

    totals = {
        "success": sum(r["success_count"] for r in rows),
        "failure": sum(r["failure_count"] for r in rows),
        "total": sum(r["total_count"] for r in rows),
    }
    return {"clients": rows, "totals": totals}
