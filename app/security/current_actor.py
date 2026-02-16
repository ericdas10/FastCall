from dataclasses import dataclass
from typing import Literal, Optional
from fastapi import Depends, HTTPException
from app.security.jwt import get_current_claims


ActorType = Literal["call_center", "client"]

@dataclass(frozen=True)
class CurrentActor:
    actor_type: ActorType
    actor_id: int
    call_center_id: Optional[int] = None

def get_current_actor(claims: dict = Depends(get_current_claims)) -> CurrentActor:
    actor_type = claims.get("actor_type")
    actor_id = claims.get("actor_id")
    call_center_id = claims.get("call_center_id")

    if actor_type not in ("call_center", "client") or actor_id is None:
        raise HTTPException(status_code=401, detail="Invalid token claims")

    return CurrentActor(
        actor_type=actor_type,
        actor_id=int(actor_id),
        call_center_id=int(call_center_id) if call_center_id is not None else None,
    )