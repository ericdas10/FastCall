from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine


# Statement keywords we explicitly refuse on the call-center DB. We only allow
# read-only SELECT (or WITH ... SELECT) statements.
_FORBIDDEN_KEYWORDS = (
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "DROP ",
    "ALTER ",
    "TRUNCATE ",
    "CREATE ",
    "GRANT ",
    "REVOKE ",
    "REPLACE ",
    "MERGE ",
    "CALL ",
    "EXEC ",
    "EXECUTE ",
    "ATTACH ",
)


class CallCenterDB:
    """
    Thin wrapper around a call-center's own database.

    On construction the schema is introspected so the operator agent can be
    given an accurate description of available tables/columns. The only public
    write surface is :py:meth:`run_select` which validates that the supplied
    statement is read-only.
    """

    def __init__(self, database_uri: Optional[str]) -> None:
        self.uri = database_uri or ""
        self.engine: Optional[Engine] = None
        self.schema: Dict[str, List[Dict[str, str]]] = {}
        self.error: Optional[str] = None

        if not self.uri:
            return

        try:
            self.engine = create_engine(self.uri, pool_pre_ping=True, future=True)
            self.schema = self._introspect()
        except Exception as e:  # pragma: no cover - defensive
            self.engine = None
            self.error = str(e)

    # ---------- introspection ----------

    def _introspect(self) -> Dict[str, List[Dict[str, str]]]:
        if self.engine is None:
            return {}
        insp = inspect(self.engine)
        out: Dict[str, List[Dict[str, str]]] = {}
        for name in insp.get_table_names():
            cols = []
            for c in insp.get_columns(name):
                cols.append({"name": c["name"], "type": str(c["type"])})
            out[name] = cols
        return out

    def schema_summary(self) -> str:
        if self.error:
            return f"(database not connected: {self.error})"
        if not self.schema:
            return "(no database connected)"
        lines = []
        for tbl, cols in self.schema.items():
            colstr = ", ".join(f"{c['name']} {c['type']}" for c in cols)
            lines.append(f"- {tbl}({colstr})")
        return "\n".join(lines)

    def is_connected(self) -> bool:
        return self.engine is not None

    # ---------- safe execution ----------

    def run_select(self, sql: str, *, max_rows: int = 50) -> Dict[str, Any]:
        """Run a single SELECT (or WITH ... SELECT) statement.

        Returns ``{"columns", "rows", "row_count"}`` on success or
        ``{"error": "..."}`` on validation/runtime failure.
        """
        if self.engine is None:
            return {"error": "No database is connected for this call center."}

        if not isinstance(sql, str):
            return {"error": "SQL must be a string."}

        cleaned = sql.strip().rstrip(";").strip()
        if not cleaned:
            return {"error": "SQL is empty."}

        if ";" in cleaned:
            return {"error": "Multiple statements are not allowed."}

        upper = cleaned.upper()
        if not (upper.startswith("SELECT") or upper.startswith("WITH ")):
            return {"error": "Only SELECT (or WITH ... SELECT) queries are allowed."}

        for kw in _FORBIDDEN_KEYWORDS:
            if kw in upper:
                return {"error": f"Disallowed keyword: {kw.strip()}"}

        try:
            with self.engine.connect() as conn:
                rs = conn.execute(text(cleaned))
                cols = list(rs.keys())
                raw = rs.fetchmany(max_rows)
                rows = [
                    {c: _to_jsonable(v) for c, v in zip(cols, r)} for r in raw
                ]
            return {"columns": cols, "rows": rows, "row_count": len(rows)}
        except Exception as e:
            return {"error": f"Query failed: {e}"}


def _to_jsonable(v: Any) -> Any:
    """Best-effort conversion so query results can be JSON-encoded."""
    try:
        import datetime
        from decimal import Decimal

        if isinstance(v, (datetime.datetime, datetime.date, datetime.time)):
            return v.isoformat()
        if isinstance(v, Decimal):
            return float(v)
        if isinstance(v, (bytes, bytearray)):
            try:
                return v.decode("utf-8", errors="replace")
            except Exception:
                return repr(v)
    except Exception:
        pass
    return v
