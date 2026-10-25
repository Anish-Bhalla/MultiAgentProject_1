"""Database bootstrap and persistence for document chunks, traces and human feedback."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import get_settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect_state() -> sqlite3.Connection:
    settings = get_settings()
    settings.state_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.state_db), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_state_db() -> None:
    with connect_state() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS document_chunks (
                chunk_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                page INTEGER,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_document_chunks_source ON document_chunks(source);
            CREATE TABLE IF NOT EXISTS traces (
                trace_id TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                route TEXT,
                answer TEXT,
                steps_json TEXT NOT NULL DEFAULT '[]',
                sources_json TEXT NOT NULL DEFAULT '[]',
                warnings_json TEXT NOT NULL DEFAULT '[]',
                duration_ms INTEGER,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trace_id TEXT NOT NULL,
                rating TEXT NOT NULL CHECK(rating IN ('positive','negative')),
                category TEXT NOT NULL DEFAULT 'other',
                comment TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )


def save_trace(trace: dict[str, Any]) -> None:
    with connect_state() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO traces
               (trace_id, query, route, answer, steps_json, sources_json, warnings_json, duration_ms, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                trace["trace_id"], trace.get("query", trace.get("question", "")), trace.get("route", "unknown"), trace.get("answer", ""),
                json.dumps(trace.get("steps", []), ensure_ascii=False),
                json.dumps(trace.get("sources", []), ensure_ascii=False),
                json.dumps(trace.get("warnings", []), ensure_ascii=False),
                int(trace.get("duration_ms", 0)), utc_now(),
            ),
        )


def get_trace(trace_id: str) -> dict[str, Any] | None:
    with connect_state() as conn:
        row = conn.execute("SELECT * FROM traces WHERE trace_id = ?", (trace_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    for src, dst in [("steps_json", "steps"), ("sources_json", "sources"), ("warnings_json", "warnings")]:
        result[dst] = json.loads(result.pop(src))
    return result


def save_feedback(trace_id: str, rating: str, category: str, comment: str) -> int:
    with connect_state() as conn:
        cur = conn.execute(
            "INSERT INTO feedback(trace_id, rating, category, comment, created_at) VALUES (?, ?, ?, ?, ?)",
            (trace_id, rating, category, comment[:2000], utc_now()),
        )
        return int(cur.lastrowid)


def list_feedback(limit: int = 100) -> list[dict[str, Any]]:
    with connect_state() as conn:
        rows = conn.execute(
            "SELECT feedback_id, trace_id, rating, category, comment, created_at FROM feedback ORDER BY feedback_id DESC LIMIT ?",
            (max(1, min(limit, 500)),),
        ).fetchall()
    return [dict(row) for row in rows]
