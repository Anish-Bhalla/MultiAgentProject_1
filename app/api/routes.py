from __future__ import annotations
import time
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from app.agents.graph import run_research
from app.config import get_settings
from app.database import get_trace
from app.feedback.service import record_feedback, recent_feedback
from app.observability.trace import persist_trace
from app.rag.ingestion import ingest_all_documents
from app.rag.store import list_documents
from app.mcp.client import MCPToolClient
from app.schemas import ChatRequest, FeedbackRequest

router = APIRouter()


@router.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "llm_enabled": bool(settings.llm_enabled and settings.openai_api_key),
        "rag_mode": settings.rag_retrieval_mode,
        "indexed_documents": len(list_documents()),
    }


@router.post("/api/chat")
async def chat(request: ChatRequest):
    trace_id = str(uuid.uuid4())
    start = time.monotonic()
    try:
        result = await run_research(request.question, trace_id=trace_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Research workflow failed: {exc}") from exc
    duration = int((time.monotonic() - start) * 1000)
    response = {
        "trace_id": trace_id,
        "query": request.question,
        "question": request.question,
        "session_id": request.session_id,
        "route": result.get("route", "unknown"),
        "plan": result.get("plan", {}),
        "answer": result.get("answer", "No answer was produced."),
        "sources": result.get("sources", []),
        "steps": result.get("steps", []),
        "warnings": result.get("warnings", []),
        "verification": result.get("verification", {}),
        "sql": (result.get("sql_result") or {}).get("sql"),
        "duration_ms": duration,
    }
    persist_trace(response)
    return response


@router.get("/api/documents")
async def documents():
    return {"documents": list_documents(), "documents_dir": str(get_settings().docs_path)}


@router.post("/api/documents/ingest")
async def ingest_documents():
    # Only files already present in configured data/documents are processed; the API accepts no arbitrary paths.
    result = await run_in_threadpool(ingest_all_documents)
    return result


@router.post("/api/feedback")
async def feedback(request: FeedbackRequest):
    trace = get_trace(request.trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found. Submit feedback against a completed chat response.")
    try:
        feedback_id = record_feedback(request.trace_id, request.rating, request.category, request.comment)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "saved", "feedback_id": feedback_id, "trace_id": request.trace_id}


@router.get("/api/feedback")
async def feedback_records(limit: int = 50):
    return {"feedback": recent_feedback(limit)}


@router.get("/api/traces/{trace_id}")
async def trace_details(trace_id: str):
    result = get_trace(trace_id)
    if not result:
        raise HTTPException(status_code=404, detail="Trace not found")
    return result


@router.get("/api/mcp/servers")
async def mcp_servers():
    return {"servers": MCPToolClient().configured_servers()}


@router.get("/api/mcp/servers/{server_name}/tools")
async def mcp_tools(server_name: str):
    try:
        tools = await MCPToolClient().list_tools(server_name)
        return {"server": server_name, "tools": tools}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
