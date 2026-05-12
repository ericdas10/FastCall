from __future__ import annotations

from threading import Lock
from typing import Dict

from app.agent.coordinator import Coordinator
from app.agent.operator import Operator


_coordinator = Coordinator()
_operators: Dict[int, Operator] = {}
_lock = Lock()


def get_operator(call_center_id: int) -> Operator:
    """
    Return a cached :class:`Operator` for the given call center, building one
    on first access. The Coordinator handles knowledge-base indexing and DB
    schema introspection at build time.
    """
    with _lock:
        op = _operators.get(call_center_id)
        if op is None:
            ctx = _coordinator.build(call_center_id)
            op = Operator(ctx)
            _operators[call_center_id] = op
        return op


def reset_operator(call_center_id: int) -> None:
    """Drop the cached operator (e.g. after KB or DB-uri changes)."""
    with _lock:
        _operators.pop(call_center_id, None)
