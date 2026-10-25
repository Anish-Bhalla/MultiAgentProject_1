"""Project-owned MCP server exposing bounded research and business-data tools."""
from __future__ import annotations
import ipaddress
import socket
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup
from mcp.server import MCPServer
from app.config import get_settings
from app.rag.store import search_documents
from app.sql.executor import execute_readonly_sql, get_schema

mcp = MCPServer("enterprise-intelligence-tools", instructions="Approved business-data and public research tools for the Enterprise Intelligence Agent.", version="1.0.0")


@mcp.tool()
def search_company_documents(query: str, top_k: int = 5) -> dict:
    """Search the indexed local document corpus and return snippets with source metadata."""
    try:
        result = search_documents(query, max(1, min(int(top_k), 10)))
        return result
    except Exception as exc:
        return {"error": f"Document search failed: {exc}", "results": []}


@mcp.tool()
def get_business_schema() -> dict:
    """Return the allowlisted business database tables and columns; no internal SQLite metadata."""
    try:
        return {"schema": get_schema()}
    except Exception as exc:
        return {"error": str(exc)}


@mcp.tool()
def execute_business_select(sql: str) -> dict:
    """Execute one validated read-only SELECT against the demo business database."""
    try:
        return execute_readonly_sql(sql)
    except Exception as exc:
        return {"error": str(exc), "sql": sql, "read_only": True}


def _check_public_host(host: str) -> None:
    if not host:
        raise ValueError("URL must include a hostname.")
    if host.lower() in {"localhost", "localhost.localdomain"}:
        raise ValueError("Localhost URLs are blocked.")
    try:
        addresses = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError("Hostname could not be resolved.") from exc
    for item in addresses:
        address = ipaddress.ip_address(item[4][0])
        if address.is_private or address.is_loopback or address.is_link_local or address.is_reserved or address.is_multicast or address.is_unspecified:
            raise ValueError("Private, local, and reserved IP destinations are blocked.")


def _safe_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only HTTP(S) URLs are allowed.")
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are blocked.")
    _check_public_host(parsed.hostname or "")
    return url


@mcp.tool()
def fetch_public_url(url: str, max_chars: int = 12000) -> dict:
    """Fetch readable text from a public HTTP(S) page; rejects local/private destinations."""
    try:
        current = _safe_url(url)
        body = ""
        page_title = current
        with httpx.Client(timeout=get_settings().web_timeout_seconds, follow_redirects=False, headers={"User-Agent": "PortfolioResearchAgent/1.0"}) as client:
            for _ in range(4):
                with client.stream("GET", current) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        location = response.headers.get("location")
                        if not location:
                            return {"url": current, "error": "Redirect response had no Location header."}
                        next_url = _safe_url(urljoin(current, location))
                        current = next_url
                        continue
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    if "text/" not in content_type and "html" not in content_type and "xml" not in content_type:
                        return {"url": current, "error": f"Unsupported content type: {content_type}"}
                    declared_size = response.headers.get("content-length")
                    if declared_size and declared_size.isdigit() and int(declared_size) > 2_000_000:
                        return {"url": current, "error": "Page exceeds 2 MB limit."}
                    # Stream the response and stop once the cap is reached instead of
                    # downloading an unbounded response before checking its size.
                    downloaded = bytearray()
                    for block in response.iter_bytes():
                        downloaded.extend(block)
                        if len(downloaded) > 2_000_000:
                            return {"url": current, "error": "Page exceeds 2 MB limit."}
                    html_text = bytes(downloaded).decode(response.encoding or "utf-8", errors="replace")
                    soup = BeautifulSoup(html_text, "html.parser")
                    page_title = soup.title.get_text(" ", strip=True) if soup.title else current
                    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                        tag.decompose()
                    body = "\n".join(fragment.strip() for fragment in soup.stripped_strings)
                    break
        if not body:
            return {"url": current, "title": page_title, "text": "", "warning": "No readable text returned."}
        return {"url": current, "title": page_title, "text": body[:max(500, min(int(max_chars), 20000))]}
    except Exception as exc:
        return {"url": url, "error": str(exc)}


@mcp.tool()
def search_web(query: str, max_results: int = 5) -> dict:
    """Search the public web. Uses Brave API when configured, otherwise the DDGS free search package."""
    settings = get_settings()
    limit = max(1, min(int(max_results), 8))
    try:
        if settings.brave_search_api_key:
            response = httpx.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": limit},
                headers={"Accept": "application/json", "X-Subscription-Token": settings.brave_search_api_key},
                timeout=settings.web_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            hits = payload.get("web", {}).get("results", [])
            results = [{"title": x.get("title", ""), "url": x.get("url", ""), "snippet": x.get("description", "")} for x in hits[:limit]]
            return {"query": query, "provider": "brave", "results": results}
        try:
            from ddgs import DDGS
            raw = list(DDGS().text(query, max_results=limit))
            results = [{"title": x.get("title", ""), "url": x.get("href", ""), "snippet": x.get("body", "")} for x in raw[:limit]]
            return {"query": query, "provider": "ddgs", "results": results}
        except Exception as exc:
            return {"query": query, "results": [], "warning": f"Web search unavailable. Set BRAVE_SEARCH_API_KEY or check DDGS connectivity: {exc}"}
    except Exception as exc:
        return {"query": query, "results": [], "warning": f"Web search failed: {exc}"}


if __name__ == "__main__":
    # MCP stdio protocol uses stdout; avoid print/debug output to stdout in this process.
    mcp.run(transport="stdio")
