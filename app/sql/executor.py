from __future__ import annotations
import sqlite3
import time
from typing import Any
from app.config import get_settings
from app.sql.validator import validate_select_sql


def get_schema() -> dict[str, list[dict[str, str]]]:
    conn = sqlite3.connect(get_settings().business_db.as_uri() + "?mode=ro", uri=True)
    try:
        schema: dict[str, list[dict[str, str]]] = {}
        for table in ("customers", "products", "orders", "order_items"):
            rows = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
            schema[table] = [{"column": row[1], "type": row[2]} for row in rows]
        return schema
    finally:
        conn.close()


def execute_readonly_sql(sql: str) -> dict[str, Any]:
    safe_sql = validate_select_sql(sql)
    settings = get_settings()
    uri = settings.business_db.as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=settings.sql_timeout_seconds)
    conn.row_factory = sqlite3.Row
    started = time.monotonic()
    conn.set_progress_handler(lambda: 1 if time.monotonic() - started > settings.sql_timeout_seconds else 0, 5000)
    try:
        cursor = conn.execute(safe_sql)
        columns = [d[0] for d in (cursor.description or [])]
        rows = cursor.fetchmany(settings.max_sql_rows + 1)
        truncated = len(rows) > settings.max_sql_rows
        rows = rows[:settings.max_sql_rows]
        return {
            "sql": safe_sql,
            "columns": columns,
            "rows": [dict(row) for row in rows],
            "row_count": len(rows),
            "truncated": truncated,
            "read_only": True,
        }
    except sqlite3.OperationalError as exc:
        if "interrupted" in str(exc).lower():
            raise TimeoutError("SQL query exceeded its time limit.") from exc
        raise
    finally:
        conn.close()
