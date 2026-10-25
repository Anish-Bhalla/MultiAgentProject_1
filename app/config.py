from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Environment-backed settings. Defaults make the project runnable locally."""

    app_name: str = "MCP Enterprise Intelligence Agent"
    environment: str = "development"
    log_level: str = "INFO"
    app_data_dir: str = str(ROOT_DIR / "data")
    documents_dir: str = str(ROOT_DIR / "data" / "documents")
    business_db_path: str = str(ROOT_DIR / "data" / "demo_business.sqlite")
    state_db_path: str = str(ROOT_DIR / "data" / "app_state.sqlite")
    mcp_config_path: str = str(ROOT_DIR / "config" / "mcp_servers.json")

    # LLM is optional. Without a key, deterministic demo-mode planning/synthesis is used.
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"
    llm_enabled: bool = True

    # BM25 works without model downloads. Set dense/hybrid after installing requirements-dense.txt.
    rag_retrieval_mode: str = "bm25"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    chroma_dir: str = str(ROOT_DIR / "data" / "chroma")
    rag_chunk_chars: int = 1200
    rag_chunk_overlap: int = 180
    rag_top_k: int = 5

    brave_search_api_key: str | None = None
    max_sql_rows: int = 200
    sql_timeout_seconds: float = 2.0
    web_timeout_seconds: float = 12.0

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def data_path(self) -> Path:
        return Path(self.app_data_dir).resolve()

    @property
    def docs_path(self) -> Path:
        return Path(self.documents_dir).resolve()

    @property
    def business_db(self) -> Path:
        return Path(self.business_db_path).resolve()

    @property
    def state_db(self) -> Path:
        return Path(self.state_db_path).resolve()

    @property
    def mcp_config(self) -> Path:
        return Path(self.mcp_config_path).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.data_path.mkdir(parents=True, exist_ok=True)
    settings.docs_path.mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)
    return settings
