from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from threading import Lock
from typing import Any, Dict, List

from app.agent.config import agent_settings


@dataclass
class AgentTurn:
    role: str  # "user" | "assistant"
    content: str
    ts: float = field(default_factory=time)


@dataclass
class AgentState:
    """Per-conversation state kept in-process between requests."""

    call_center_id: int
    session_id: str
    turns: List[AgentTurn] = field(default_factory=list)
    summary: str = ""
    # `slots` may include things like `turn_sources: ["kb", "db", "faq", ...]`,
    # one entry per assistant turn. The FAQ extractor uses these source labels
    # to decide which Q/A pairs are safe to add to the FAQ.
    slots: Dict[str, Any] = field(default_factory=dict)
    last_access: float = field(default_factory=time)

    def add_turn(self, role: str, content: str) -> None:
        self.turns.append(AgentTurn(role=role, content=content))
        self.last_access = time()


class AgentMemory:
    """In-memory conversation cache, keyed by (call_center_id, session_id)."""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self._states: Dict[str, AgentState] = {}
        self.ttl = ttl_seconds
        self._lock = Lock()

    @staticmethod
    def _key(call_center_id: int, session_id: str) -> str:
        return f"{call_center_id}:{session_id}"

    def get(self, call_center_id: int, session_id: str) -> AgentState:
        with self._lock:
            self._evict_expired()
            key = self._key(call_center_id, session_id)
            st = self._states.get(key)
            if st is None:
                st = AgentState(call_center_id=call_center_id, session_id=session_id)
                self._states[key] = st
            st.last_access = time()
            return st

    def reset(self, call_center_id: int, session_id: str) -> None:
        with self._lock:
            self._states.pop(self._key(call_center_id, session_id), None)

    def _evict_expired(self) -> None:
        now = time()
        for k in list(self._states.keys()):
            if now - self._states[k].last_access > self.ttl:
                self._states.pop(k, None)


_memory = AgentMemory(ttl_seconds=agent_settings.memory_ttl_seconds)


def get_memory() -> AgentMemory:
    return _memory
