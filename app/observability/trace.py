"""Lightweight local trace persistence and JSON-friendly trace logging."""
import logging
from typing import Any
from app.database import save_trace

logger = logging.getLogger(__name__)


def persist_trace(payload: dict[str, Any]) -> None:
    save_trace(payload)
    logger.info(
        "agent_trace_completed",
        extra={
            "trace_id": payload.get("trace_id"),
            "route": payload.get("route"),
            "duration_ms": payload.get("duration_ms"),
            "source_count": len(payload.get("sources", [])),
            "warning_count": len(payload.get("warnings", [])),
        },
    )
