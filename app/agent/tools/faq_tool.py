from __future__ import annotations

import json
import math
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

from app.agent.config import agent_settings, cc_data_dir
from app.agent.openai_client import embed_texts


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    s = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        s += x * y
        na += x * x
        nb += y * y
    if na == 0.0 or nb == 0.0:
        return 0.0
    return s / (math.sqrt(na) * math.sqrt(nb))


class FaqStore:
    """
    Per-call-center FAQ persisted as a JSON file at
    ``data/cc_<id>/faq.json``.

    Each entry has the form ``{"question", "answer", "embedding"}``. Lookup
    uses cosine similarity over OpenAI embeddings. New entries are appended
    only when no sufficiently-similar existing entry covers the question.
    """

    def __init__(self, call_center_id: int, *, threshold: Optional[float] = None) -> None:
        self.call_center_id = call_center_id
        self.threshold = (
            threshold if threshold is not None else agent_settings.faq_similarity_threshold
        )
        self.path: Path = cc_data_dir(call_center_id) / "faq.json"
        self._lock = Lock()
        self.entries: List[Dict[str, Any]] = self._load()

    # ---------- persistence ----------

    def _load(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            return []
        except Exception:
            return []

    def _save(self) -> None:
        self.path.write_text(
            json.dumps(self.entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ---------- public API ----------

    def lookup(self, question: str) -> Optional[Dict[str, Any]]:
        question = (question or "").strip()
        if not question or not self.entries:
            return None
        try:
            q_emb = embed_texts([question])[0]
        except Exception:
            return None

        best: Optional[Dict[str, Any]] = None
        best_score = 0.0
        for e in self.entries:
            emb = e.get("embedding") or []
            sc = _cosine(q_emb, emb)
            if sc > best_score:
                best_score = sc
                best = e
        if best is not None and best_score >= self.threshold:
            return {
                "question": best.get("question", ""),
                "answer": best.get("answer", ""),
                "score": best_score,
            }
        return None

    def add(self, question: str, answer: str) -> bool:
        """Append a generic Q/A. Returns True if it was added."""
        question = (question or "").strip()
        answer = (answer or "").strip()
        if not question or not answer:
            return False
        existing = self.lookup(question)
        if existing and existing.get("score", 0.0) >= self.threshold:
            return False
        try:
            emb = embed_texts([question])[0]
        except Exception:
            return False
        with self._lock:
            self.entries.append(
                {"question": question, "answer": answer, "embedding": emb}
            )
            self._save()
        return True


class FaqTool:
    """Operator-callable wrapper over :class:`FaqStore`."""

    name = "faq_lookup"
    description = (
        "Check whether the user's question has already been answered in the "
        "call center's FAQ. Use this FIRST for generic questions to reduce "
        "latency. If `answer` is null, fall back to other tools."
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Generic, paraphrased version of the user's question.",
            }
        },
        "required": ["query"],
    }

    def __init__(self, store: FaqStore) -> None:
        self.store = store

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = (args or {}).get("query", "") or ""
        hit = self.store.lookup(query)
        if not hit:
            return {"answer": None}
        return {
            "answer": hit["answer"],
            "matched_question": hit["question"],
            "score": hit["score"],
        }
