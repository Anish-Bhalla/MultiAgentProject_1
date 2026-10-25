"""Optional OpenAI-compatible LLM adapter. The application remains usable without credentials."""
from functools import lru_cache
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from app.config import get_settings


@lru_cache(maxsize=1)
def get_llm():
    settings = get_settings()
    if not settings.llm_enabled or not settings.openai_api_key:
        return None
    kwargs = {
        "model": settings.openai_model,
        "api_key": settings.openai_api_key,
        "temperature": 0,
        "timeout": 40,
        "max_retries": 1,
    }
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return ChatOpenAI(**kwargs)
