from __future__ import annotations
from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    query: str
    trace_id: str
    plan: dict[str, Any]
    sql_result: dict[str, Any]
    rag_result: dict[str, Any]
    web_result: dict[str, Any]
    verification: dict[str, Any]
    answer: str
    route: str
    sources: list[dict[str, Any]]
    steps: list[dict[str, Any]]
    warnings: list[str]
