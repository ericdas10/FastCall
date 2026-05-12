from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from app.agent.config import agent_settings
from app.agent.openai_client import get_openai
from app.agent.tools.faq_tool import FaqStore


log = logging.getLogger(__name__)


# Heuristic patterns for "personal / account-specific" content that must NEVER
# be promoted to a generic FAQ entry.
_PERSONAL_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w.-]+\.\w+"),                # emails
    re.compile(r"\b\+?\d[\d\s().\-]{6,}\b"),             # phones / long numbers
    re.compile(r"\b\d{4,}\b"),                            # account / order ids
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),    # dates
]


def _looks_personal(text: str) -> bool:
    if not text:
        return False
    for pat in _PERSONAL_PATTERNS:
        if pat.search(text):
            return True
    return False


def _build_pairs(turns: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Pair each user turn with the next assistant turn."""
    pairs: List[Dict[str, str]] = []
    pending_user: str | None = None
    for t in turns:
        role = t.get("role")
        content = (t.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            pending_user = content
        elif role == "assistant" and pending_user is not None:
            pairs.append({"q": pending_user, "a": content})
            pending_user = None
    return pairs


def extract_faq_from_ticket(payload: Dict[str, Any], faq_store: FaqStore) -> int:
    """
    Process a successfully-closed conversation payload and append generic Q/A
    pairs to the call center's FAQ.

    Rules:
      * Only assistant turns whose source label is ``kb`` or ``llm`` are
        considered. ``db``-sourced turns and ``faq``-sourced turns are skipped
        (the latter are already in the FAQ; the former contain customer data).
      * Pairs containing emails / phones / IDs / dates on either side are
        rejected.
      * The remaining candidates are sent to the LLM, which is asked to keep
        only those that are reusable and to rephrase them generically.

    Returns the number of newly-added FAQ entries.
    """
    turns: List[Dict[str, Any]] = payload.get("turns") or []
    slots: Dict[str, Any] = payload.get("slots") or {}
    sources: List[str] = list(slots.get("turn_sources") or [])

    pairs = _build_pairs(turns)
    if not pairs:
        return 0

    # Align ``sources`` (one per assistant turn) with our pair list. They are
    # in the same order: the i-th assistant turn corresponds to the i-th source.
    candidates: List[Dict[str, str]] = []
    for i, p in enumerate(pairs):
        src = sources[i] if i < len(sources) else "llm"
        if src in ("db", "faq"):
            continue
        if _looks_personal(p["q"]) or _looks_personal(p["a"]):
            continue
        candidates.append(p)

    if not candidates:
        return 0

    items = _generalize_with_llm(candidates)
    added = 0
    for it in items:
        q = (it.get("question") or "").strip()
        a = (it.get("answer") or "").strip()
        if not q or not a:
            continue
        if _looks_personal(q) or _looks_personal(a):
            continue
        if faq_store.add(q, a):
            added += 1
    return added


def _generalize_with_llm(candidates: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Ask the LLM to rephrase candidates into clean generic FAQ entries and to
    drop those that are too specific.
    """
    try:
        client = get_openai()
    except Exception as e:
        log.warning("FAQ extractor: OpenAI client unavailable: %s", e)
        return []

    sys = (
        "You are extracting reusable FAQ entries from a closed customer-support "
        "conversation. Keep only Q/A pairs that are GENERIC and reusable for "
        "future customers (no personal data, no specific names, no account "
        "numbers, no dates, no monetary amounts tied to one customer). "
        "Rewrite each kept pair as a clean, paraphrased generic question and "
        "a concise answer. Drop pairs that are not reusable. "
        "Return STRICT JSON of the form "
        '{"items":[{"question":"...","answer":"..."}, ...]}'
    )

    payload = json.dumps(candidates, ensure_ascii=False)

    try:
        resp = client.chat.completions.create(
            model=agent_settings.chat_model,
            messages=[
                {"role": "system", "content": sys},
                {"role": "user", "content": payload},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
        items = data.get("items") or []
        if not isinstance(items, list):
            return []
        return [it for it in items if isinstance(it, dict)]
    except Exception as e:
        log.warning("FAQ extractor: LLM generalization failed: %s", e)
        return []
