from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

from app.persistence.db import SessionLocal
from app.model.call_centers.model import CallCenters

from app.agent.config import agent_settings
from app.agent.kb_indexer import collect_chunks
from app.agent.schema import CallCenterDB
from app.agent.vector_store import get_vector_store
from app.agent.tools.faq_tool import FaqStore, FaqTool
from app.agent.tools.rag_tool import RagTool
from app.agent.tools.db_tool import DbQueryTool


log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are the customer-service operator for "{name}".

About this call center:
{description}

You have access to the following tools (call them when useful):
- faq_lookup(query): try this FIRST for generic questions; it returns a cached answer if one exists.
- rag_search(query, top_k?): search the call center's knowledge base (PDFs / docs / policies) for general information.
- {db_tool_line}

DATABASE SCHEMA (use only with run_sql_select):
{schema}

Conversation rules:
- Be concise, friendly and professional. Keep replies under ~6 sentences.
- NEVER invent data. If tools return nothing relevant, say so politely and ask for the missing detail.
- For account-specific questions ({db_required_hint}) you MUST use run_sql_select with the customer's name.
- Cite generic information from rag_search/faq_lookup; do not mention internal tool names to the user.
- If the user indicates the conversation is finished (e.g. "thanks, bye"), acknowledge briefly and stop.
"""


@dataclass
class OperatorContext:
    """Bundle of everything an :class:`Operator` needs."""

    call_center_id: int
    system_prompt: str
    vector_store: object
    faq_store: FaqStore
    db: CallCenterDB
    tools: Dict[str, object]


class Coordinator:
    """
    The main agent. For a given call_center_id it:

    * loads `description`, `knowledge_base_path` and `database_uri` from the
      `call_centers` table;
    * (re)indexes the knowledge base into Chroma (per-tenant collection);
    * connects to the call center's database (read-only) and introspects schema;
    * builds the operator's tools and system prompt.
    """

    def build(self, call_center_id: int) -> OperatorContext:
        with SessionLocal() as session:
            cc = session.get(CallCenters, call_center_id)
            if cc is None:
                raise ValueError(f"Call center {call_center_id} does not exist")
            name = cc.name or f"Call center #{call_center_id}"
            description = cc.description or "(no description provided)"
            kb_path = cc.knowledge_base_path or ""
            db_uri = cc.database_uri or ""

        # 1) Vector store + (re)index KB
        vstore = get_vector_store(call_center_id)
        try:
            chunks = collect_chunks(kb_path)
            if chunks:
                count = vstore.index_documents(documents=chunks)
                log.info(
                    "Agent[cc=%s]: indexed %s KB chunks from '%s'",
                    call_center_id,
                    count,
                    kb_path,
                )
            else:
                log.info(
                    "Agent[cc=%s]: KB path '%s' produced no chunks (skipping index)",
                    call_center_id,
                    kb_path,
                )
        except Exception as e:  # pragma: no cover - defensive
            log.warning("Agent[cc=%s]: KB indexing failed: %s", call_center_id, e)

        # 2) DB connection
        db = CallCenterDB(db_uri)

        # 3) FAQ store
        faq_store = FaqStore(call_center_id=call_center_id)

        # 4) Tools
        tools: Dict[str, object] = {}
        faq_tool = FaqTool(faq_store)
        rag_tool = RagTool(vstore, default_top_k=agent_settings.top_k)
        tools[faq_tool.name] = faq_tool
        tools[rag_tool.name] = rag_tool
        if db.is_connected():
            db_tool = DbQueryTool(db)
            tools[db_tool.name] = db_tool

        # 5) System prompt
        if db.is_connected():
            db_tool_line = (
                "run_sql_select(sql): query the call center's database for "
                "facts about a specific customer (read-only)."
            )
            db_required_hint = (
                "any question that depends on a specific customer's data"
            )
        else:
            db_tool_line = (
                "(no database is connected for this call center; "
                "do NOT promise account-specific answers)"
            )
            db_required_hint = (
                "if the user asks for account-specific data, explain that the "
                "call center has not connected a customer database"
            )

        prompt = SYSTEM_PROMPT.format(
            name=name,
            description=description,
            schema=db.schema_summary(),
            db_tool_line=db_tool_line,
            db_required_hint=db_required_hint,
        )

        return OperatorContext(
            call_center_id=call_center_id,
            system_prompt=prompt,
            vector_store=vstore,
            faq_store=faq_store,
            db=db,
            tools=tools,
        )
