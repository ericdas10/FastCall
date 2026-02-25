from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json

from app.rag.config import rag_settings
from app.rag.loaders import load_docs_from_dir
from app.rag.chunking import chunk_docs
from app.rag.index import RagIndex
from app.rag.llm import LocalLlm
from app.rag.memory_store import RagCache

FALLBACK_MESSAGE = "I can't find a relevant answer for your question"

def _cc_dir(call_center_id: int) -> Path:
    return rag_settings.data_dir / f"cc_{call_center_id}"


@dataclass
class RagPipeline:
    def __post_init__(self):
        self.llm = LocalLlm()
        self.cache = RagCache(ttl_seconds=getattr(rag_settings, "memory_ttl_seconds", 3600))

    def ensure_index(self, *, call_center_id: int) -> RagIndex:
        base_dir = _cc_dir(call_center_id)
        idx = RagIndex(base_dir=base_dir, embedding_model_name=rag_settings.embedding_model)

        if not idx.exists():
            docs_dir = base_dir / "docs"
            docs_dir.mkdir(parents=True, exist_ok=True)

            docs = load_docs_from_dir(docs_dir)
            chunks = chunk_docs(docs)
            idx.build(chunks)

        return idx

    def answer(self, *, call_center_id: int, session_id: str, question: str) -> str:
        idx = self.ensure_index(call_center_id=call_center_id)
        state = self.cache.get_session(call_center_id, session_id)

        state.add_turn("user", question)

        standalone_query = self._rewrite_query(question=question, state=state)

        cached = self.cache.retrieval_get(call_center_id, standalone_query)
        if cached:
            results = cached["results"]
        else:
            results = idx.search_hybrid(standalone_query, top_k=rag_settings.top_k, alpha=getattr(rag_settings, "hybrid_alpha", 0.65))
            self.cache.retrieval_set(call_center_id, standalone_query, {"results": results})

        if not results:
            resp = FALLBACK_MESSAGE
            state.add_turn("assistant", resp)
            return resp

        results = results[: rag_settings.top_k]

        context_blocks = []
        for r in results:
            context_blocks.append(f"[chunk_id={r.chunk_id} source={r.source}]\n{r.text}")
        context = "\n\n---\n\n".join(context_blocks)

        llm_json = self._grounded_answer(question=question, standalone_query=standalone_query, state=state, context=context)

        answer = (llm_json.get("answer") or "").strip()
        answerable = bool(llm_json.get("answerable"))
        follow_up = llm_json.get("follow_up_question")

        if (not answerable) or (not answer) or (answer == rag_settings.fallback_message):
            resp = follow_up.strip() if isinstance(follow_up, str) and follow_up.strip() else FALLBACK_MESSAGE
            state.add_turn("assistant", resp)
            self._maybe_update_summary(state)
            return resp

        state.add_turn("assistant", answer)
        self._maybe_update_summary(state)

        return answer

    def _rewrite_query(self, *, question: str, state) -> str:
        prompt = f"""
            You are rewriting a user's message into a standalone search query for retrieval.
            Use the conversation summary + recent turns to resolve pronouns and missing references.
            Return ONLY the rewritten query (no quotes, no explanations).
            
            Conversation summary:
            {state.summary or "(none)"}
            
            Recent turns:
            {state.short_history(6)}
            
            User message:
            {question}
            
            Standalone query:
            """
        out = self.llm.generate(prompt=prompt).strip()
        return out if out else question

    def _grounded_answer(self, *, question: str, standalone_query: str, state, context: str) -> dict:
        """
        Force the model to:
        - only answer from context
        - otherwise ask ONE clarifying question
        - output strict JSON
        """
        prompt = f"""
            You are a friendly, professional call-center virtual agent.
            Your goal is to help the customer efficiently and naturally.
            
            Rules (very important):
            - Use ONLY the CONTEXT to answer. If the answer is not supported by the context, do NOT guess.
            - If not answerable, ask exactly ONE concise clarifying question that would unlock the answer.
            - Keep the answer short, human, and action-oriented.
            - Do not mention "context", "chunks", "retrieval", or internal system details.
            - Output MUST be valid JSON with keys: answerable (boolean), answer (string), follow_up_question (string).
            
            Conversation summary:
            {state.summary or "(none)"}
            
            User question:
            {question}
            
            Standalone query (for retrieval):
            {standalone_query}
            
            CONTEXT:
            {context}
            
            JSON:
            """
        raw = self.llm.generate(prompt=prompt).strip()
        try:
            clean_raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_raw)
        except Exception:
            print(f"LLM JSON failure: {raw}")
            return {"answerable": False, "answer": "", "follow_up_question": rag_settings.fallback_message}

    def _maybe_update_summary(self, state) -> None:
        if len(state.turns) % 8 != 0:
            return

        prompt = f"""
            Summarize the conversation so far for future assistance.
            Include:
            - customer goal / issue
            - constraints (account, product, timeframe)
            - any preferences
            Keep it compact (max 8 lines). No bullet spam.
            
            Conversation:
            {state.short_history(20)}
            
            Existing summary:
            {state.summary or "(none)"}
            
            New summary:
            """
        summ = self.llm.generate(prompt=prompt).strip()
        if summ:
            state.summary = summ
