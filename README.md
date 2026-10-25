# MCP Enterprise Intelligence Agent

**A portfolio-grade agent application combining LangGraph orchestration, MCP tools, RAG, safe Text-to-SQL, external research, evidence checks, evaluation and human feedback.**

The application investigates a business question across three sources: structured business data, a local document corpus, and optional external web research. It returns an answer with source metadata and an execution trace.

> **Important demo-data note:** the included sales database and two Markdown corpus files are synthetic. They are only for repeatable software testing. Do not present their outputs as real company performance. Add public/appropriately licensed company filings to `data/documents/` to create a real document corpus. If you add real company reports, do not combine them with the synthetic SQL metrics as if both describe the same company; first load matching structured financial data into the SQL database.

## What it demonstrates

- **Agent orchestration:** LangGraph state graph with planner, concurrent specialist agents, evidence verifier and synthesizer.
- **MCP:** Uses the current MCP Python SDK v2 client/server APIs; a project-owned MCP server exposes document search, database schema, read-only SQL execution, web search and public-page fetch tools. The host supports stdio and Streamable HTTP transports. See the [official SDK docs](https://py.sdk.modelcontextprotocol.io/).
- **RAG:** PDF/Markdown/text ingestion, overlapping chunks, persistent chunk metadata, BM25 retrieval, citations, optional SentenceTransformers + Chroma hybrid retrieval.
- **Text-to-SQL:** optional LLM-generated SQL, deterministic no-key fallback, SQLGlot parsing, table allowlist, read-only SQLite connection, timeouts and row caps.
- **Human feedback:** thumbs up/down, error categories, comments and persistent trace association.
- **Evaluation:** tests plus a routing smoke benchmark.
- **Operations:** FastAPI, browser UI, structured execution trace, Docker Compose and GitHub Actions CI.

## 1. Quick start (no paid API key required)

Requirements: Python 3.11 or newer, `pip`, and (optionally) Docker. The official MCP Python SDK v2 targets Python 3.11+; use a dedicated virtual environment.

```bash
# 1) From the project root
python3.11 -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate

# 2) Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3) Create local settings
cp .env.example .env                      # Windows: copy .env.example .env

# 4) Initialize sample data and index included demo documents
python -m scripts.init_demo_db
python -m scripts.ingest_documents

# 5) Start the API and browser UI
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000**. API docs are at **http://127.0.0.1:8000/docs**.

Without an API key, the app is in **demo mode**: the planner uses deterministic rules, SQL uses templates for common questions, and the synthesizer produces an evidence summary. This mode is useful for testing data flow and security controls, but it is not a generative answer experience.

### Try these questions

- `Show total revenue by quarter`
- `Who are the top 5 customers by revenue?`
- `What does the quarterly update say about gross margin?`
- `Compare top products by revenue with the quarterly update's demand commentary`
- `Find the latest news about outdoor retail industry trends`

Some web-search results depend on your current network and upstream provider availability.

## 2. Enable an OpenAI-compatible LLM (optional)

Edit `.env`:

```dotenv
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
# Optional: compatible providers may expose an OpenAI-style endpoint
# OPENAI_BASE_URL=https://your-provider.example/v1
LLM_ENABLED=true
```

Restart the app. When a key is configured, the planner can select tools semantically, the SQL agent can generate SQL from the database schema, and the synthesizer can write a natural-language report grounded in retrieved evidence. Model/API charges and quotas depend on the provider. Do not commit `.env` to Git.

## 3. Add public company reports to the RAG corpus

1. Download quarterly results, investor presentations or transcripts from a company investor-relations page or an exchange filing source. See [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md).
2. Put `.pdf`, `.md`, `.markdown` or `.txt` files into `data/documents/`.
3. Run `python -m scripts.ingest_documents` or click **Re-index documents** in the UI.
4. Ask questions requiring cross-quarter comparison and check the cited filenames/pages.

The pipeline does not silently download third-party filings. You should review source/date, document terms and the accuracy of extracted PDF text. Scanned PDFs may need OCR, which is not bundled.

## 4. Optional dense / hybrid retrieval

Default retrieval uses BM25 and has no embedding model download. To add semantic retrieval:

```bash
pip install -r requirements-dense.txt
```

Then in `.env` set:

```dotenv
RAG_RETRIEVAL_MODE=hybrid
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

Re-run document ingestion. The embedding model downloads the first time; this can require several hundred MB of disk space and Internet access. Chroma persists its local index under `data/chroma/`. Hybrid mode combines BM25 and dense ranks using reciprocal-rank fusion. For a production deployment, consider a server-backed vector database and stronger reranking/evaluation; this local persistent setup is a portfolio/development configuration. See [Chroma documentation](https://docs.trychroma.com/reference/python).

## 5. MCP servers and tools

`config/mcp_servers.json` is the MCP server registry used by the app. The default `local_research` server is started as a stdio subprocess and exposes:

| MCP tool | Purpose | Safety boundary |
|---|---|---|
| `search_company_documents` | Search indexed document chunks | Local corpus only |
| `get_business_schema` | List approved table/column metadata | Hides SQLite internal tables |
| `execute_business_select` | Run generated SQL | SELECT-only validation, allowlisted tables, read-only DB, timeout, row cap |
| `search_web` | Public web search | DDGS fallback; optional Brave API key |
| `fetch_public_url` | Fetch readable public web-page text | HTTP(S) only, blocks private/local IPs, limited response size/redirects |

The app also includes disabled examples for external MCP servers:

- **Fetch:** see the [official MCP Fetch server](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch). It is an open-source server package, not necessarily a free public hosted endpoint; you run it locally using its documented installation method.
- **GitHub:** see the [official GitHub MCP Server](https://github.com/github/github-mcp-server). Docker and an appropriately scoped GitHub token are needed for the included example.

To enable one, install its prerequisites and flip `enabled` to `true` in `config/mcp_servers.json`; secrets should be environment variables, never hard-coded. The generic client supports stdio and Streamable HTTP entries. For Streamable HTTP, configure `transport`, `url` and any required auth headers for a server you trust. Avoid arbitrary public MCP endpoints, especially those asking for broad account permissions.

MCP server packages are free/open-source where their repositories say so, but upstream hosted services, API quotas, network usage and terms may vary. This repository does not rely on an unverified third-party public MCP server to start.

## 6. Evaluation and tests

```bash
pytest
python -m scripts.run_eval
```

The routing evaluator reports whether all expected tools were selected for a small test set. It is a smoke test, not evidence of answer accuracy. Read [docs/EVALUATION.md](docs/EVALUATION.md) for a path toward retrieval recall, SQL execution accuracy, citation validity, answer faithfulness, task success and cost/latency metrics.

Human feedback is saved with trace ID, rating, error category and optional comment. Feedback is **not** immediately used to fine-tune a model; use it to triage bugs and carefully curate future evaluation data.

## 7. Docker

```bash
cp .env.example .env
docker compose up --build
```

Then visit `http://127.0.0.1:8000`. Docker Compose mounts `data/` for persistence. If you use external MCP servers, make sure their runtime and required secrets are available to the container. The included endpoint has no authentication: do not expose it directly to the public Internet.

## 8. Key API endpoints

| Method | Endpoint | Use |
|---|---|---|
| GET | `/health` | Health + mode flags |
| POST | `/api/chat` | Run multi-agent investigation |
| GET | `/api/documents` | View indexed document sources |
| POST | `/api/documents/ingest` | Re-index files in configured corpus directory |
| POST | `/api/feedback` | Submit feedback against a trace |
| GET | `/api/feedback` | Inspect local feedback records |
| GET | `/api/traces/{trace_id}` | Inspect persisted trace |
| GET | `/api/mcp/servers` | List configured MCP servers |
| GET | `/api/mcp/servers/{server_name}/tools` | Discover a server's MCP tools |

## 9. Security and limitations

- Keep this development app on localhost or behind appropriate authentication and authorization.
- Only connect MCP servers you trust. Tool descriptions and retrieved web/document text are untrusted inputs.
- The SQL database uses read-only execution plus AST validation, but production SQL requires database-level least privilege, isolation and query governance.
- The public fetch tool is a sample with SSRF controls, not a complete production egress-security solution.
- No semantic guarantee is made by the verifier; human evaluation is still needed.
- The local SQLite stores are for single-machine development. Use a shared, secure database and durable checkpoints for multi-user deployment.
- The project is decision support, not a fully autonomous business operator. Any consequential external action should require human approval.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [File-by-file guide](docs/FILE_GUIDE.md)
- [Public company data sources](docs/DATA_SOURCES.md)
- [Evaluation + feedback](docs/EVALUATION.md)
