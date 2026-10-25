# Architecture

```text
Browser / API client
        |
        v
FastAPI ── request validation, trace ID, response serialization
        |
        v
LangGraph StateGraph
        |
        +--> Supervisor / Planner ── decides SQL, RAG, web, or a combination
        |
        +--> Research stage (independent agents run concurrently)
        |       +--> SQL agent ── schema -> optional LLM SQL generation -> MCP tool
        |       +--> RAG agent ── MCP document-search tool -> indexed evidence
        |       +--> Web research agent ── MCP search/fetch tools
        |
        +--> Evidence verifier ── source index, metadata checks, warnings
        |
        +--> Synthesizer ── grounded answer with [S1]-style citations
        |
        v
Trace store + human feedback store (SQLite)
```

## MCP boundary

The application acts as an MCP host/client using the current MCP Python SDK v2 API. `config/mcp_servers.json` declares servers and transports. The project-owned server in `app/mcp_servers/local_tools.py` exposes five tools. The same client wrapper can connect to configured stdio servers and Streamable HTTP servers. Optional third-party servers are disabled by default until you configure them.

The SQL tool has layered controls: SQLGlot parses the single statement, a table allowlist rejects unrelated tables, a timeout limits long queries, the connection uses SQLite read-only mode, and result rows are capped. This is good portfolio defense-in-depth, not a substitute for production IAM, isolated execution, or a security review.

## RAG pipeline

`data/documents/` -> PDF/Markdown/text extraction -> overlapping chunks -> persistent SQLite chunk store -> BM25 retrieval. Optional dense/hybrid mode adds SentenceTransformers + Chroma and reciprocal-rank fusion. Each retrieved chunk retains its file and page metadata for citations.

## Demo vs. configured LLM mode

With no `OPENAI_API_KEY`, the app uses heuristic routing, deterministic SQL templates and a transparent evidence summary. With an OpenAI-compatible endpoint configured, the planner, SQL generator and synthesizer can use the LLM. This separation makes local tests reproducible and lets you develop before paying for model calls.

## Current limitations / next engineering steps

- MCP sessions are created per tool call; pool sessions before putting this behind high-throughput traffic.
- The local API has no user authentication or tenant isolation; keep it on localhost during development.
- The public URL fetch tool applies SSRF protections, but production deployments need a hardened egress proxy and DNS-rebinding defenses.
- The verifier checks provenance metadata, not semantic truth. Build a human-reviewed test set and model-assisted claim verification before claiming high factual accuracy.
- Feedback is logged for evaluation; it does not automatically change model weights.
- The bundled transaction database and sample documents are synthetic. Add licensed/public documents to `data/documents/` for your own research corpus.
