from __future__ import annotations
import re
from urllib.parse import urlparse
from app.mcp.client import MCPToolClient


async def run_research_agent(query: str, mcp: MCPToolClient) -> dict:
    direct_url = re.search(r"https?://[^\s)<>]+", query)
    if direct_url:
        page = await mcp.call_tool("local_research", "fetch_public_url", {"url": direct_url.group(0), "max_chars": 10000})
        if isinstance(page, dict) and page.get("text") and not page.get("error"):
            return {"query": query, "provider": "direct_url", "results": [], "fetched_pages": [{"title": page.get("title", direct_url.group(0)), "url": page.get("url", direct_url.group(0)), "text": page["text"]}]}
        error = page.get("error") or page.get("warning") if isinstance(page, dict) else str(page)
        return {"query": query, "provider": "direct_url", "results": [], "fetched_pages": [], "warning": error or "Could not fetch the supplied URL."}

    result = await mcp.call_tool("local_research", "search_web", {"query": query, "max_results": 5})
    if isinstance(result, str):
        return {"query": query, "results": [], "warning": result[:1000]}
    results = result.get("results", []) if isinstance(result, dict) else []
    fetched = []
    # Fetch at most two search results for grounded context, and only accept well-formed HTTP URLs.
    for hit in results[:2]:
        url = hit.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        try:
            page = await mcp.call_tool("local_research", "fetch_public_url", {"url": url, "max_chars": 5000})
            if isinstance(page, dict) and page.get("text"):
                fetched.append({"title": hit.get("title", page.get("title", "Web page")), "url": page.get("url", url), "snippet": page.get("snippet", ""), "text": page["text"]})
        except Exception:
            continue
    result["fetched_pages"] = fetched
    return result
