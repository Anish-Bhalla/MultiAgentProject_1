# File-by-file project guide

This guide describes the source files and the reason each exists. Start with `README.md`, then follow the request lifecycle in [ARCHITECTURE.md](ARCHITECTURE.md).

## Root and configuration

| File | What it does | Why it exists |
|---|---|---|
| `README.md` | Setup, example questions, configuration, APIs and limitations | Main user/developer instructions |
| `.env.example` | Safe template for environment variables | Keeps API keys out of source code |
| `.gitignore` | Excludes secrets, virtual environments, databases and local vector indexes | Prevents accidental credential/data commits |
| `.dockerignore` | Excludes local-only files and generated artifacts from Docker build context | Keeps images smaller and avoids copying secrets or local state |
| `requirements.txt` | Core dependencies | Installs the local app without the heavier optional embedding stack |
| `requirements-dense.txt` | Adds Chroma and SentenceTransformers | Enables semantic/vector retrieval when desired |
| `pyproject.toml` | pytest configuration | Keeps test invocation consistent |
| `Dockerfile` | Builds the API container | Reproducible deployment package |
| `docker-compose.yml` | Runs the app and persists the data directory | Easy local container operation |
| `LICENSE` | MIT license for this starter code | Makes reuse terms explicit |
| `config/mcp_servers.json` | Registry of MCP server commands, arguments, transports and environment values | Lets the host discover/connect to local or remote tools without hard-coding every server into the graph |

## Supporting documentation

| File | What it covers |
|---|---|
| `docs/ARCHITECTURE.md` | Request lifecycle, agent responsibilities, MCP boundaries and security assumptions |
| `docs/DATA_SOURCES.md` | Where to collect public company filings and how to add them to the RAG corpus |
| `docs/EVALUATION.md` | Baseline metrics, evaluation dataset design and feedback-to-improvement workflow |
| `docs/FILE_GUIDE.md` | This explanation of each repository file |
| `data/.gitkeep` | Keeps the otherwise generated-data directory in Git; local databases and indexes should not be committed |

## Application entry and common services

| File | What it does | Key concepts to review |
|---|---|---|
| `app/main.py` | Creates the FastAPI app, initializes local data stores, mounts the UI and registers routes | Application lifecycle / startup hooks |
| `app/config.py` | Loads environment-backed settings and resolves data paths | Configuration management, optional LLM and RAG modes |
| `app/logging_config.py` | Configures application logging | Diagnosing failures without printing secrets |
| `app/schemas.py` | Validates incoming chat and feedback payloads with Pydantic | Input validation and typed API contracts |
| `app/database.py` | Creates the local app-state database and persists document chunks, traces and feedback | SQLite schema, trace storage, feedback records |
| `app/llm.py` | Creates an optional OpenAI-compatible LangChain chat client | Model provider abstraction and no-key fallback |
| `app/static/index.html` | Lightweight browser UI for questions, sources, traces, indexing and ratings | Calling APIs safely from a browser without a frontend framework |

## Multi-agent orchestration

| File | What it does | Key concepts to review |
|---|---|---|
| `app/agents/state.py` | Defines shared graph state | State schema and inter-agent handoff |
| `app/agents/graph.py` | Builds and runs the LangGraph workflow: planner → research → verifier → synthesizer | Graph orchestration, async work, timing, trace steps |
| `app/agents/planner.py` | Chooses SQL/RAG/web tasks using an LLM when configured or deterministic rules otherwise | Routing, task decomposition, structured planning |
| `app/agents/sql_agent.py` | Gets schema, generates SQL and calls the SQL MCP tool | Text-to-SQL pipeline |
| `app/agents/rag_agent.py` | Calls the document-search MCP tool | Separating retrieval responsibility from orchestration |
| `app/agents/research_agent.py` | Searches the web and fetches up to two public result pages, or fetches a user-supplied URL | Tool use, source gathering and failure handling |
| `app/agents/verifier.py` | Builds a source index and records provenance checks/warnings | Evidence tracking; note this is not a semantic proof of truth |
| `app/agents/synthesizer.py` | Uses an optional LLM to create a cited report; otherwise renders a deterministic report | Grounded generation, source IDs, deterministic fallback |

## MCP client and server

| File | What it does | Key concepts to review |
|---|---|---|
| `app/mcp/client.py` | Reads the MCP registry, expands environment variables, connects via stdio or Streamable HTTP, discovers and calls tools | MCP host/client, transports, server isolation, tool schema discovery |
| `app/mcp_servers/local_tools.py` | Implements the local MCP server exposing database, document, search and fetch tools | Defining typed MCP tools, error boundaries, public URL restrictions |

## SQL subsystem

| File | What it does | Key concepts to review |
|---|---|---|
| `app/sql/demo_database.py` | Creates reproducible synthetic customers, products, orders and order-items | Demo data bootstrap; synthetic data is clearly labelled |
| `app/sql/generator.py` | Generates SQL with the configured LLM or deterministic templates | Schema-constrained SQL generation and graceful fallback |
| `app/sql/validator.py` | Parses SQL, allows a single SELECT-based statement, restricts tables and blocks dangerous operations/functions | SQL AST inspection and query safety |
| `app/sql/executor.py` | Opens the demo DB read-only, applies a progress timeout and caps rows | Database-level guardrails beyond model prompting |

## RAG subsystem

| File | What it does | Key concepts to review |
|---|---|---|
| `app/rag/ingestion.py` | Extracts PDF/text/Markdown content, chunks it and stores source/page metadata | Parsing, chunking, provenance |
| `app/rag/store.py` | Stores chunks in SQLite, ranks with BM25 and optionally fuses dense + lexical results | Retrieval, persistence, reciprocal rank fusion |
| `app/rag/dense.py` | Optional Chroma + SentenceTransformers indexing and search | Dense embeddings and vector search; imports are optional at runtime |
| `data/documents/demo_quarterly_business_update.md` | Synthetic quarterly update used by default demo RAG | Reproducible document questions; not a real filing |
| `data/documents/demo_data_dictionary.md` | Explains the synthetic SQL dataset and revenue definition | Helps agent users understand the demo schema |

## Feedback, observability, API

| File | What it does | Key concepts to review |
|---|---|---|
| `app/feedback/service.py` | Validates trace existence and records user ratings | Feedback lifecycle and triage |
| `app/observability/trace.py` | Persists the completed run and emits an operational log event | Traces, timing and basic metrics |
| `app/api/routes.py` | Implements chat, health, ingestion, feedback, trace and MCP-inspection endpoints | HTTP contracts, error responses and async orchestration |

## Scripts, evaluation and tests

| File | What it does | Why it matters |
|---|---|---|
| `scripts/init_demo_db.py` | Initializes app state + the demo business database | Repeatable setup |
| `scripts/ingest_documents.py` | Re-indexes documents under `data/documents/` | Repeatable RAG ingestion |
| `scripts/run_eval.py` | Measures whether required tools were selected for fixed questions | A first, limited agent-routing evaluation |
| `evaluation/datasets/routing_cases.json` | Contains routing cases and expected tools | Versioned test data |
| `tests/test_api.py` | Tests startup/health and browser UI | API smoke tests |
| `tests/test_database.py` | Tests read-only querying and schema exposure | Data bootstrap and SQL executor checks |
| `tests/test_mcp_integration.py` | Starts the actual local MCP server and checks tool discovery/call | Integration coverage for the protocol boundary |
| `tests/test_rag.py` | Tests chunking, route selection and fusion | Retrieval utility checks |
| `tests/test_sql_validator.py` | Tests allowed and blocked SQL statements | Security regression tests |
| `.github/workflows/ci.yml` | Installs core dependencies and runs pytest on pushes/PRs | CI/CD baseline |

## Package initializers

`app/__init__.py`, `app/agents/__init__.py`, `app/api/__init__.py`, `app/feedback/__init__.py`, `app/mcp/__init__.py`, `app/mcp_servers/__init__.py`, `app/observability/__init__.py`, `app/rag/__init__.py`, `app/sql/__init__.py` and `scripts/__init__.py` mark Python package directories. They are intentionally small.

## Recommended reading order for reviewing/modifying the code

1. `app/agents/graph.py` — the whole workflow.
2. `app/agents/planner.py` — why each tool gets called.
3. `app/mcp/client.py` and `app/mcp_servers/local_tools.py` — how tool calls cross the MCP boundary.
4. `app/sql/validator.py` / `executor.py` — what stops unsafe SQL.
5. `app/rag/ingestion.py` / `store.py` — how a source document becomes retrievable evidence.
6. `app/agents/verifier.py` / `synthesizer.py` — how results turn into a cited report.
7. `tests/` and `evaluation/` — how to know whether a code change broke behavior.
