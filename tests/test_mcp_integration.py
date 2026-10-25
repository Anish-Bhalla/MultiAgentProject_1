import pytest
from app.database import init_state_db
from app.mcp.client import MCPToolClient
from app.rag.ingestion import ingest_all_documents
from app.sql.demo_database import init_business_db


@pytest.mark.asyncio
async def test_local_mcp_server_exposes_tools():
    init_state_db()
    init_business_db()
    ingest_all_documents()
    client = MCPToolClient()
    tools = await client.list_tools("local_research")
    names = {tool["name"] for tool in tools}
    assert {"search_company_documents", "get_business_schema", "execute_business_select", "search_web", "fetch_public_url"}.issubset(names)
    schema = await client.call_tool("local_research", "get_business_schema", {})
    assert "orders" in schema["schema"]
