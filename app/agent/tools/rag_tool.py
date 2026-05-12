from __future__ import annotations

from typing import Any, Dict

from app.agent.vector_store import CallCenterVectorStore


class RagTool:
    """
    Knowledge-base search tool exposed to the operator agent. Backed by the
    call-center-specific Chroma collection, so per-tenant isolation is
    guaranteed by construction.
    """

    name = "rag_search"
    description = (
        "Search the call center's knowledge base (PDFs, docs, policies) for "
        "information that may answer the user's question. Use it for general "
        "questions about products, policies, processes, hours, etc. Returns "
        "the most relevant snippets."
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A focused, paraphrased version of the user's question.",
            },
            "top_k": {
                "type": "integer",
                "description": "Optional. Number of snippets to return.",
                "minimum": 1,
                "maximum": 10,
            },
        },
        "required": ["query"],
    }

    def __init__(self, store: CallCenterVectorStore, default_top_k: int = 6) -> None:
        self.store = store
        self.default_top_k = default_top_k

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = (args or {}).get("query", "") or ""
        top_k = int((args or {}).get("top_k") or self.default_top_k)
        if not query.strip():
            return {"results": [], "note": "Empty query."}
        results = self.store.search(query, top_k=top_k)
        # Trim payload sent back to the model: keep distance for transparency
        # but cap text to a sane size to keep prompts compact.
        trimmed = []
        for r in results:
            txt = r.get("text", "") or ""
            if len(txt) > 1500:
                txt = txt[:1500] + "..."
            trimmed.append(
                {
                    "text": txt,
                    "source": r.get("source", ""),
                    "distance": r.get("distance"),
                }
            )
        return {"results": trimmed, "count": len(trimmed)}
