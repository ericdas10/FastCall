from __future__ import annotations

from typing import Any, Dict

from app.agent.schema import CallCenterDB


class DbQueryTool:
    """
    Schema-aware read-only SQL tool. The operator agent receives the database
    schema in its system prompt and uses this tool to ask questions about a
    specific customer (lookup by name) or any other read-only fact stored in
    the call center's own database.
    """

    name = "run_sql_select"
    description = (
        "Run a single read-only SELECT (or WITH ... SELECT) query against the "
        "call center's database. Use this for customer-specific questions "
        "(e.g. 'What is John Doe's last invoice?'). Refer to the database "
        "schema in the system prompt. Multiple statements, mutations and "
        "DDL are rejected. Use SQL string literals for values; do NOT include "
        "a trailing semicolon."
    )
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "A single SELECT statement. No semicolons, no DDL/DML.",
            }
        },
        "required": ["sql"],
    }

    def __init__(self, db: CallCenterDB) -> None:
        self.db = db

    def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        sql = (args or {}).get("sql", "") or ""
        return self.db.run_select(sql)
