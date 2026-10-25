from __future__ import annotations
from app.mcp.client import MCPToolClient
from app.config import get_settings


async def run_rag_agent(query: str, mcp: MCPToolClient) -> dict:
    result = await mcp.call_tool("local_research", "search_company_documents", {
        "query": query, "top_k": get_settings().rag_top_k,
    })
    if isinstance(result, str):
        return {"query": query, "results": [], "error": result[:1000]}
    return result
