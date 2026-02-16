from __future__ import annotations
from dataclasses import dataclass, field
from time import time
from typing import Dict, List, Optional, Any
import hashlib
import json

@dataclass
class ChatTurn:
    role: str  # "user" | "assistant"
    content: str
    ts: float = field(default_factory=lambda: time())

@dataclass
class ConversationState:
    session_id: str
    call_center_id: int
    turns: List[ChatTurn] = field(default_factory=list)
    summary: str = ""
    slots: Dict[str, Any] = field(default_factory=dict)  # customer facts/preferences/issue
    last_access_ts: float = field(default_factory=lambda: time())

    def add_turn(self, role: str, content: str):
        self.turns.append(ChatTurn(role=role, content=content))
        self.last_access_ts = time()

    def short_history(self, n: int = 8) -> str:
        recent = self.turns[-n:]
        lines = []
        for t in recent:
            prefix = "User" if t.role == "user" else "Assistant"
            lines.append(f"{prefix}: {t.content}")
        return "\n".join(lines)

class RagCache:
    """
    In-memory cache:
    - conversation state per (call_center_id, session_id)
    - retrieval cache per (call_center_id, normalized_query_hash)
    """
    def __init__(self, *, ttl_seconds: int = 3600, max_sessions: int = 2000, max_queries: int = 5000):
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self.max_queries = max_queries
        self._sessions: Dict[str, ConversationState] = {}
        self._retrieval: Dict[str, dict] = {}

    def _session_key(self, call_center_id: int, session_id: str) -> str:
        return f"{call_center_id}:{session_id}"

    def get_session(self, call_center_id: int, session_id: str) -> ConversationState:
        self._evict_expired()
        key = self._session_key(call_center_id, session_id)
        st = self._sessions.get(key)
        if st is None:
            st = ConversationState(session_id=session_id, call_center_id=call_center_id)
            self._sessions[key] = st
        st.last_access_ts = time()
        self._cap_sessions()
        return st

    def retrieval_get(self, call_center_id: int, query: str) -> Optional[dict]:
        self._evict_expired()
        key = self._retrieval_key(call_center_id, query)
        item = self._retrieval.get(key)
        if not item:
            return None
        if time() - item["ts"] > self.ttl_seconds:
            self._retrieval.pop(key, None)
            return None
        return item

    def retrieval_set(self, call_center_id: int, query: str, payload: dict):
        self._evict_expired()
        key = self._retrieval_key(call_center_id, query)
        self._retrieval[key] = {"ts": time(), **payload}
        self._cap_queries()

    def _retrieval_key(self, call_center_id: int, query: str) -> str:
        norm = " ".join(query.lower().split())
        h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
        return f"{call_center_id}:{h}"

    def _evict_expired(self):
        now = time()
        # sessions
        for k in list(self._sessions.keys()):
            if now - self._sessions[k].last_access_ts > self.ttl_seconds:
                self._sessions.pop(k, None)
        # retrieval
        for k in list(self._retrieval.keys()):
            if now - self._retrieval[k]["ts"] > self.ttl_seconds:
                self._retrieval.pop(k, None)

    def _cap_sessions(self):
        if len(self._sessions) <= self.max_sessions:
            return
        # evict LRU-ish
        items = sorted(self._sessions.items(), key=lambda kv: kv[1].last_access_ts)
        for k, _ in items[: max(1, len(items) - self.max_sessions)]:
            self._sessions.pop(k, None)

    def _cap_queries(self):
        if len(self._retrieval) <= self.max_queries:
            return
        items = sorted(self._retrieval.items(), key=lambda kv: kv[1]["ts"])
        for k, _ in items[: max(1, len(items) - self.max_queries)]:
            self._retrieval.pop(k, None)
