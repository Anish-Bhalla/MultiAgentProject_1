from __future__ import annotations
from app.mcp.client import MCPToolClient
from app.sql.generator import generate_sql


async def run_sql_agent(query: str, mcp: MCPToolClient) -> dict:
    schema = await mcp.call_tool("local_research", "get_business_schema", {})
    sql, generation_method = await generate_sql(query)
    result = await mcp.call_tool("local_research", "execute_business_select", {"sql": sql})
    if isinstance(result, str):
        return {"error": "MCP returned non-JSON SQL result", "raw": result[:1000], "sql": sql}
    result.setdefault("sql", sql)
    result["generation_method"] = generation_method
    result["schema"] = schema.get("schema", {}) if isinstance(schema, dict) else {}
    if generation_method == "heuristic_fallback_after_llm_error":
        result.setdefault("warning", "LLM SQL generation failed; a deterministic fallback query was used. Verify that it matches the request.")
    if result.get("error"):
        result["warning"] = "The SQL tool rejected or could not execute this query. No database changes were made."
    return result
