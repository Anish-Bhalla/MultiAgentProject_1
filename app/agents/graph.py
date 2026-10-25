from __future__ import annotations
import asyncio
import time
import uuid
from typing import Any
from langgraph.graph import END, START, StateGraph
from app.agents.state import AgentState
from app.agents.planner import make_plan
from app.agents.sql_agent import run_sql_agent
from app.agents.rag_agent import run_rag_agent
from app.agents.research_agent import run_research_agent
from app.agents.verifier import verify_evidence
from app.agents.synthesizer import synthesize
from app.mcp.client import MCPToolClient

_mcp = MCPToolClient()


def _step(name: str, status: str, duration_ms: int, detail: str = "") -> dict[str, Any]:
    return {"step": name, "status": status, "duration_ms": duration_ms, "detail": detail[:500]}


async def planner_node(state: AgentState) -> dict[str, Any]:
    start = time.monotonic()
    plan = await make_plan(state["query"])
    duration = int((time.monotonic() - start) * 1000)
    route = "+".join(plan.get("tasks", [])) or "rag"
    return {
        "plan": plan,
        "route": route,
        "steps": list(state.get("steps", [])) + [_step("supervisor_planner", "completed", duration, f"Selected tools: {route}; intent={plan.get('intent')}")],
        "warnings": list(state.get("warnings", [])),
    }


async def research_node(state: AgentState) -> dict[str, Any]:
    plan = state.get("plan", {})
    tasks = []
    task_names = []
    if plan.get("use_sql"):
        task_names.append("sql")
        tasks.append(run_sql_agent(state["query"], _mcp))
    if plan.get("use_rag"):
        task_names.append("rag")
        tasks.append(run_rag_agent(state["query"], _mcp))
    if plan.get("use_web"):
        task_names.append("web")
        tasks.append(run_research_agent(state["query"], _mcp))
    starts = time.monotonic()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    duration = int((time.monotonic() - starts) * 1000)
    update: dict[str, Any] = {"steps": list(state.get("steps", [])), "warnings": list(state.get("warnings", []))}
    mapping = {"sql": "sql_result", "rag": "rag_result", "web": "web_result"}
    for name, result in zip(task_names, results):
        if isinstance(result, Exception):
            update["warnings"].append(f"{name.upper()} agent failed: {result}")
            update["steps"].append(_step(f"{name}_agent", "failed", duration, str(result)))
        else:
            update[mapping[name]] = result
            update["steps"].append(_step(f"{name}_agent", "completed", duration, f"Finished {name} evidence retrieval"))
    return update


async def verifier_node(state: AgentState) -> dict[str, Any]:
    start = time.monotonic()
    checked = verify_evidence(state)
    duration = int((time.monotonic() - start) * 1000)
    steps = list(state.get("steps", [])) + [_step("evidence_verifier", "completed", duration, f"Collected {checked['verification']['source_count']} evidence sources")]
    return {**checked, "steps": steps}


async def synthesis_node(state: AgentState) -> dict[str, Any]:
    start = time.monotonic()
    answer = await synthesize(state)
    duration = int((time.monotonic() - start) * 1000)
    # synthesize() may append a fallback warning; explicitly return state updates
    # rather than relying on in-place mutation being preserved by the graph.
    warnings = list(state.get("warnings", []))
    return {
        "answer": answer,
        "warnings": warnings,
        "steps": list(state.get("steps", [])) + [_step("answer_synthesizer", "completed", duration, "Generated evidence-backed report or demo-mode summary")],
    }


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("plan", planner_node)
    workflow.add_node("research", research_node)
    workflow.add_node("verify", verifier_node)
    workflow.add_node("synthesize", synthesis_node)
    workflow.add_edge(START, "plan")
    workflow.add_edge("plan", "research")
    workflow.add_edge("research", "verify")
    workflow.add_edge("verify", "synthesize")
    workflow.add_edge("synthesize", END)
    return workflow.compile()


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


async def run_research(query: str, trace_id: str | None = None) -> dict[str, Any]:
    initial: AgentState = {"query": query, "trace_id": trace_id or str(uuid.uuid4()), "steps": [], "warnings": []}
    result = await get_graph().ainvoke(initial)
    return dict(result)
