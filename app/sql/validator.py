"""Defence-in-depth SQL validation. SQLite read-only mode is the final execution boundary."""
from __future__ import annotations
import re
import sqlglot
from sqlglot import exp

ALLOWED_TABLES = {"customers", "products", "orders", "order_items"}
DENIED_FUNCTIONS = {"load_extension", "readfile", "writefile", "fts3_tokenizer"}


class SQLSafetyError(ValueError):
    pass


def validate_select_sql(sql: str) -> str:
    if not sql or not sql.strip():
        raise SQLSafetyError("SQL is empty.")
    if len(sql) > 8000:
        raise SQLSafetyError("SQL exceeds the allowed length.")
    # Remove fenced code blocks and only accept a single statement.
    cleaned = re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql.strip(), flags=re.IGNORECASE)
    try:
        parsed = [tree for tree in sqlglot.parse(cleaned, read="sqlite") if tree is not None]
    except Exception as exc:
        raise SQLSafetyError(f"SQL could not be parsed: {exc}") from exc
    if len(parsed) != 1:
        raise SQLSafetyError("Only one SQL statement is permitted.")
    tree = parsed[0]
    if not isinstance(tree, (exp.Select, exp.Union, exp.Subquery)):
        raise SQLSafetyError("Only SELECT queries (including SELECT-based CTEs) are allowed.")
    # INSERT/UPDATE/DELETE/MERGE/DDL nested in any expression is blocked too.
    for node in tree.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Command, exp.Into)):
            raise SQLSafetyError(f"Unsafe SQL operation detected: {type(node).__name__}.")
        if isinstance(node, exp.Anonymous) and node.name.lower() in DENIED_FUNCTIONS:
            raise SQLSafetyError(f"Function '{node.name}' is not allowed.")
    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        name = (table.name or "").lower()
        if not name or name.startswith("sqlite_") or name in {"sqlite_master", "sqlite_schema"}:
            raise SQLSafetyError("SQLite internal tables are not available.")
        if name not in ALLOWED_TABLES and name not in cte_names:
            raise SQLSafetyError(f"Table '{name}' is not allowlisted. Allowed tables: {', '.join(sorted(ALLOWED_TABLES))}.")
        if table.db or table.catalog:
            raise SQLSafetyError("Qualified database/catalog access is not allowed.")
    return tree.sql(dialect="sqlite")
