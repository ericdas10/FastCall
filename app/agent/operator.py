from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Set

from app.agent.config import agent_settings
from app.agent.coordinator import OperatorContext
from app.agent.memory import AgentState
from app.agent.openai_client import get_openai


log = logging.getLogger(__name__)


_CLOSE_KEYWORDS = (
    "bye", "goodbye", "no, that's all", "no that's all", "thats all",
    "that's all", "no more questions", "we're done", "we are done",
    "im done", "i'm done", "thank you, bye", "thanks bye", "no thanks",
    "asta e tot", "am terminat", "la revedere", "multumesc, pa",
    "mulțumesc, pa", "mulțumesc pa",
)


class Operator:
    """
    Conversational agent for a single call center.

    A single instance is reused across all conversations belonging to its
    call center; the per-conversation state lives in
    :class:`app.agent.memory.AgentState`.
    """

    def __init__(self, ctx: OperatorContext) -> None:
        self.ctx = ctx
        self.client = get_openai()

    # ---------- public API ----------

    def answer(
        self,
        *,
        state: AgentState,
        question: str,
        customer: Optional[Dict] = None,
    ) -> Dict:
        """
        Process a single user message. Returns:
            { "answer": str, "conversation_finished": bool, "source": str }

        ``source`` is one of: ``faq``, ``kb``, ``db``, ``llm`` (for plain
        chat answers). It is appended to ``state.slots["turn_sources"]``
        so that the FAQ extractor can later filter out DB-sourced turns.

        ``customer`` is the authenticated client's identity (first_name,
        last_name, email, client_id). It is injected per-turn into the model's
        context so the LLM can use the right values in ``run_sql_select``
        for account-specific questions.
        """
        question = (question or "").strip()
        if not question:
            return {
                "answer": agent_settings.fallback_message,
                "conversation_finished": False,
                "source": "llm",
            }

        state.add_turn("user", question)

        # Fast path: cached FAQ answer
        try:
            faq_hit = self.ctx.faq_store.lookup(question)
        except Exception as e:  # pragma: no cover - defensive
            log.warning("FAQ lookup failed for cc=%s: %s", self.ctx.call_center_id, e)
            faq_hit = None

        if faq_hit:
            answer = faq_hit["answer"]
            state.add_turn("assistant", answer)
            state.slots.setdefault("turn_sources", []).append("faq")
            return {
                "answer": answer,
                "conversation_finished": self._user_signals_close(question),
                "source": "faq",
            }

        # Tool-using LLM path
        answer, sources_used = self._run_with_tools(
            state=state, question=question, customer=customer
        )

        if not answer:
            answer = agent_settings.fallback_message

        source_label = self._classify_source(sources_used)
        state.add_turn("assistant", answer)
        state.slots.setdefault("turn_sources", []).append(source_label)

        return {
            "answer": answer,
            "conversation_finished": self._user_signals_close(question),
            "source": source_label,
        }

    # ---------- internals ----------

    def _run_with_tools(
        self,
        *,
        state: AgentState,
        question: str,
        customer: Optional[Dict] = None,
    ) -> tuple[str, Set[str]]:
        messages: List[Dict] = [
            {"role": "system", "content": self.ctx.system_prompt}
        ]

        # Per-turn identity injection: the authenticated customer is *not*
        # stored in AgentState (which is keyed by conversation, not by user)
        # but the LLM needs these exact values to build correct SQL for
        # account-specific questions.
        if customer:
            first = (customer.get("first_name") or "").strip()
            last = (customer.get("last_name") or "").strip()
            email = (customer.get("email") or "").strip()
            cid = customer.get("client_id")
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "AUTHENTICATED CUSTOMER (use these exact values in "
                        "run_sql_select for any account-specific question; "
                        "never ask the user for their name or email \u2014 you "
                        "already have them):\n"
                        f"- first_name: {first!r}\n"
                        f"- last_name: {last!r}\n"
                        f"- email: {email!r}\n"
                        f"- client_id: {cid!r}"
                    ),
                }
            )

        # Recent conversation context (last N turns; the just-added user turn
        # at the end IS the current question).
        recent = state.turns[-agent_settings.history_limit :]
        for t in recent:
            role = "user" if t.role == "user" else "assistant"
            messages.append({"role": role, "content": t.content})

        tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self.ctx.tools.values()
        ]

        sources_used: Set[str] = set()
        final_text: Optional[str] = None

        for _ in range(agent_settings.max_tool_iterations):
            try:
                resp = self.client.chat.completions.create(
                    model=agent_settings.chat_model,
                    messages=messages,
                    tools=tools_schema if tools_schema else None,
                    temperature=0.2,
                )
            except Exception as e:
                log.exception("LLM call failed for cc=%s: %s", self.ctx.call_center_id, e)
                return (agent_settings.fallback_message, sources_used)

            msg = resp.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None) or []

            if not tool_calls:
                final_text = (msg.content or "").strip()
                break

            # Record the assistant's tool-call message verbatim, then run each
            # tool and append the result.
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )

            for tc in tool_calls:
                tool_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except Exception:
                    args = {}

                tool = self.ctx.tools.get(tool_name)
                if tool is None:
                    result = {"error": f"Unknown tool: {tool_name}"}
                else:
                    try:
                        result = tool.run(args)
                    except Exception as e:
                        log.exception(
                            "Tool '%s' failed for cc=%s: %s",
                            tool_name,
                            self.ctx.call_center_id,
                            e,
                        )
                        result = {"error": f"Tool error: {e}"}

                sources_used.add(tool_name)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tool_name,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )

        if final_text is None:
            # Hit the iteration cap; try to coax a final answer with no tools.
            try:
                resp = self.client.chat.completions.create(
                    model=agent_settings.chat_model,
                    messages=messages
                    + [
                        {
                            "role": "system",
                            "content": (
                                "You have used your tool budget. Reply now with a "
                                "concise final answer based on what the tools "
                                "returned. Do not call any more tools."
                            ),
                        }
                    ],
                    temperature=0.2,
                )
                final_text = (resp.choices[0].message.content or "").strip()
            except Exception:
                final_text = agent_settings.fallback_message

        return (final_text or "", sources_used)

    @staticmethod
    def _classify_source(sources_used: Set[str]) -> str:
        if "run_sql_select" in sources_used:
            return "db"
        if "rag_search" in sources_used:
            return "kb"
        if "faq_lookup" in sources_used:
            return "faq"
        return "llm"

    @staticmethod
    def _user_signals_close(text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False
        return any(k in t for k in _CLOSE_KEYWORDS)
