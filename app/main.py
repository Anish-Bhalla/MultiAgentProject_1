from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.config import get_settings
from app.database import init_state_db
from app.logging_config import configure_logging
from app.rag.ingestion import ingest_all_documents
from app.rag.store import list_documents
from app.sql.demo_database import init_business_db

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.data_path.mkdir(parents=True, exist_ok=True)
    settings.docs_path.mkdir(parents=True, exist_ok=True)
    init_state_db()
    init_business_db()
    if not list_documents():
        report = ingest_all_documents()
        logger.info("Initial document ingestion: %s", report)
    logger.info("Application initialized; data directory=%s", settings.data_path)
    yield


app = FastAPI(
    title="MCP Enterprise Intelligence Agent",
    description="Multi-agent RAG + safe Text-to-SQL + MCP tools + evidence checks and human feedback.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(router)
static_dir = get_settings().data_path.parent / "app" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", include_in_schema=False)
async def home():
    return FileResponse(str(static_dir / "index.html"))
