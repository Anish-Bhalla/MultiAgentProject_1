from __future__ import annotations
from typing import Any
from urllib.parse import urlparse


def verify_evidence(state: dict[str, Any]) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    warnings: list[str] = list(state.get("warnings", []))
    next_id = 1

    sql_result = state.get("sql_result") or {}
    if sql_result:
        if sql_result.get("error"):
            warnings.append(f"SQL agent: {sql_result['error']}")
        elif sql_result.get("rows") is not None:
            sources.append({
                "id": f"S{next_id}", "type": "structured_data", "title": "Demo business database",
                "citation": "Synthetic demo sales database; inspect the attached SQL for reproducibility.",
                "sql": sql_result.get("sql", ""), "row_count": sql_result.get("row_count", 0),
                "excerpt": str(sql_result.get("rows", []))[:3000],
            })
            next_id += 1
        if sql_result.get("warning"):
            warnings.append(sql_result["warning"])

    rag_result = state.get("rag_result") or {}
    if rag_result.get("warning"):
        warnings.append(str(rag_result["warning"]))
    if rag_result.get("error"):
        warnings.append(f"RAG agent: {rag_result['error']}")
    for item in rag_result.get("results", [])[:8]:
        sources.append({
            "id": f"S{next_id}", "type": "document", "title": item.get("source", "Indexed document"),
            "citation": item.get("citation", item.get("source", "Indexed document")),
            "score": item.get("score"), "excerpt": item.get("text", "")[:2500],
            "page": item.get("page"), "url": None,
        })
        next_id += 1

    web_result = state.get("web_result") or {}
    if web_result.get("warning"):
        warnings.append(str(web_result["warning"]))
    for item in web_result.get("fetched_pages", [])[:4]:
        if item.get("url"):
            sources.append({
                "id": f"S{next_id}", "type": "web_page", "title": item.get("title", "Web page"),
                "citation": item["url"], "url": item["url"], "excerpt": item.get("text", "")[:2500],
            })
            next_id += 1
    for item in web_result.get("results", [])[:5]:
        url = item.get("url") or item.get("href")
        parsed = urlparse(url) if isinstance(url, str) else None
        if not parsed or parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        if any(s.get("url") == url for s in sources):
            continue
        sources.append({
            "id": f"S{next_id}", "type": "web_search_result", "title": item.get("title", "Search result"),
            "citation": url, "url": url, "excerpt": item.get("snippet", item.get("body", ""))[:1500],
        })
        next_id += 1

    if not sources:
        warnings.append("No source evidence was retrieved. Add documents, check database initialization, or enable web search before relying on the answer.")
    verification = {
        "source_count": len(sources),
        "has_evidence": bool(sources),
        "checks": {
            "sql_read_only_tool_used": bool(sql_result.get("read_only")) if sql_result else None,
            "document_citations_have_source": all(bool(s.get("citation")) for s in sources if s["type"] == "document"),
            "web_links_are_present": all(bool(s.get("url")) for s in sources if s["type"] in {"web_page", "web_search_result"}),
        },
        "limitations": ["Evidence presence and source metadata are checked deterministically; this is not a proof that every generated claim is correct."],
    }
    return {"sources": sources, "warnings": list(dict.fromkeys(warnings)), "verification": verification}
