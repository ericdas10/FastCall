from fastapi import APIRouter, Depends, HTTPException
from app.persistence.unit_of_work import get_uow, UnitOfWork
from app.service.conversation_service import ConversationService
from app.service.exceptions import NotFound, NotAllowed
from app.security.current_actor import get_current_actor, CurrentActor
from app.agent.registry import get_operator, reset_operator

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


@router.post("/me/agent/rebuild")
def rebuild_agent(actor: CurrentActor = Depends(get_current_actor)):
    """
    Force the coordinator to rebuild this call center's operator. Useful after
    you've added/removed files from the knowledge base or changed the
    `database_uri`. Re-indexes Chroma and re-introspects the DB schema.
    """
    _require_call_center(actor)
    reset_operator(actor.actor_id)
    try:
        op = get_operator(actor.actor_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {e}")

    db_connected = op.ctx.db.is_connected()
    return {
        "call_center_id": actor.actor_id,
        "tools": sorted(op.ctx.tools.keys()),
        "db_connected": db_connected,
        "vector_store_empty": op.ctx.vector_store.is_empty(),
        "faq_entries": len(op.ctx.faq_store.entries),
    }
