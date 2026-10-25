"""MCP host client built against the current MCP Python SDK v2 API."""
from __future__ import annotations
import json
import os
import re
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from mcp import Client, StdioServerParameters
from app.config import get_settings


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        pattern = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")
        def replace(match: re.Match[str]) -> str:
            return os.environ.get(match.group(1), match.group(2) or "")
        return pattern.sub(replace, value)
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    return value


class MCPToolClient:
    """Connects to a configured MCP server for one tool call.

    A connection per call is easy to inspect in a portfolio project. For high
    throughput, replace this with a pooled long-lived Client/session manager.
    """

    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path or get_settings().mcp_config)

    def _server_config(self, server: str) -> dict[str, Any]:
        if not self.config_path.exists():
            raise RuntimeError(f"MCP config not found: {self.config_path}")
        raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        config = raw.get(server)
        if not config:
            raise KeyError(f"MCP server '{server}' is not configured")
        config = _expand_env(config)
        if not config.get("enabled", True):
            raise RuntimeError(f"MCP server '{server}' is disabled in {self.config_path.name}")
        return config

    @asynccontextmanager
    async def _client(self, server: str) -> AsyncIterator[Client]:
        config = self._server_config(server)
        transport = config.get("transport", "stdio").lower()
        if transport == "stdio":
            settings = get_settings()
            root = Path(__file__).resolve().parents[2]
            # MCP v2 intentionally does not inherit the parent's full environment.
            # Forward only variables the local tool server needs, plus explicit config env.
            env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONPATH": str(root),
                "APP_DATA_DIR": str(settings.data_path),
                "DOCUMENTS_DIR": str(settings.docs_path),
                "BUSINESS_DB_PATH": str(settings.business_db),
                "STATE_DB_PATH": str(settings.state_db),
                "MCP_CONFIG_PATH": str(settings.mcp_config),
                "CHROMA_DIR": str(settings.chroma_dir),
                "RAG_RETRIEVAL_MODE": settings.rag_retrieval_mode,
                "EMBEDDING_MODEL": settings.embedding_model,
                "RAG_TOP_K": str(settings.rag_top_k),
                "WEB_TIMEOUT_SECONDS": str(settings.web_timeout_seconds),
                "BRAVE_SEARCH_API_KEY": settings.brave_search_api_key or "",
            }
            env.update({str(k): str(v) for k, v in config.get("env", {}).items() if v not in (None, "")})
            command = str(config.get("command") or sys.executable)
            args = [str(v) for v in config.get("args", [])]
            cwd_value = Path(str(config.get("cwd") or root))
            cwd = cwd_value if cwd_value.is_absolute() else (root / cwd_value).resolve()
            params = StdioServerParameters(command=command, args=args, env=env, cwd=str(cwd))
            async with Client(params) as client:
                yield client
        elif transport in {"streamable_http", "http"}:
            url = str(config["url"])
            headers = {str(k): str(v) for k, v in config.get("headers", {}).items()}
            if headers:
                # MCP v2 uses httpx2 for HTTP auth, headers and transport settings.
                import httpx2
                from mcp.client.streamable_http import streamable_http_client
                async with httpx2.AsyncClient(headers=headers, timeout=httpx2.Timeout(30.0, read=300.0)) as http_client:
                    transport_obj = streamable_http_client(url, http_client=http_client)
                    async with Client(transport_obj) as client:
                        yield client
            else:
                async with Client(url) as client:
                    yield client
        else:
            raise ValueError(f"Unsupported MCP transport '{transport}'. Use stdio or streamable_http.")

    async def call_tool(self, server: str, tool: str, arguments: dict[str, Any] | None = None) -> Any:
        async with self._client(server) as client:
            result = await client.call_tool(tool, arguments or {})
            if getattr(result, "is_error", False):
                texts = [getattr(item, "text", "") for item in getattr(result, "content", [])]
                raise RuntimeError("MCP tool error: " + " ".join(t for t in texts if t))
            structured = getattr(result, "structured_content", None)
            if structured is not None:
                return structured
            text_blocks = [getattr(item, "text", "") for item in getattr(result, "content", []) if getattr(item, "text", None)]
            joined = "\n".join(text_blocks)
            try:
                return json.loads(joined)
            except (ValueError, TypeError):
                return joined

    async def list_tools(self, server: str) -> list[dict[str, Any]]:
        async with self._client(server) as client:
            result = await client.list_tools()
            return [
                {"name": tool.name, "description": tool.description or "", "input_schema": tool.input_schema}
                for tool in result.tools
            ]

    def configured_servers(self) -> list[dict[str, Any]]:
        if not self.config_path.exists():
            return []
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        return [{"name": name, "enabled": bool(item.get("enabled", True)), "transport": item.get("transport", "stdio")}
                for name, item in config.items()]
