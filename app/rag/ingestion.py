from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any
from pypdf import PdfReader
from app.config import get_settings
from app.rag.store import replace_source_chunks

SUPPORTED = {".pdf", ".md", ".markdown", ".txt"}


def extract_file(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".pdf":
        output = []
        reader = PdfReader(str(path))
        for page_no, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                output.append({"text": text, "metadata": {"page": page_no, "file_type": "pdf"}})
        return output
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [{"text": text, "metadata": {"page": None, "file_type": path.suffix.lower().lstrip(".")}}] if text.strip() else []


def chunk_text(text: str, chunk_chars: int = 1200, overlap: int = 180) -> list[str]:
    text = "\n".join(line.strip() for line in text.replace("\x00", " ").splitlines() if line.strip())
    if not text:
        return []
    chunk_chars = max(200, chunk_chars)
    overlap = max(0, min(overlap, chunk_chars // 2))
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_chars)
        if end < len(text):
            boundary = max(text.rfind(". ", start, end), text.rfind("\n", start, end))
            if boundary > start + chunk_chars // 2:
                end = boundary + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def ingest_path(path: Path) -> int:
    settings = get_settings()
    path = path.resolve()
    # Only index files under the configured corpus directory; prevent path traversal.
    if settings.docs_path not in path.parents:
        raise ValueError(f"Refusing to ingest a file outside {settings.docs_path}")
    if path.suffix.lower() not in SUPPORTED or not path.is_file():
        return 0
    extracted = extract_file(path)
    all_chunks = []
    for page_item in extracted:
        pieces = chunk_text(page_item["text"], settings.rag_chunk_chars, settings.rag_chunk_overlap)
        for piece_idx, piece in enumerate(pieces):
            content_hash = hashlib.sha256(piece.encode("utf-8")).hexdigest()[:16]
            metadata = {
                "source": path.name,
                "path": path.relative_to(settings.docs_path).as_posix(),
                "page": page_item["metadata"].get("page"),
                "file_type": page_item["metadata"].get("file_type"),
                "content_hash": content_hash,
                "chunk_index": piece_idx,
            }
            all_chunks.append({"text": piece, "metadata": metadata})
    count = replace_source_chunks(path.relative_to(settings.docs_path).as_posix(), all_chunks)
    mode = settings.rag_retrieval_mode.lower()
    if count and mode in {"dense", "hybrid"}:
        from app.rag.dense import index_chunks
        index_chunks(path.relative_to(settings.docs_path).as_posix(), all_chunks)
    return count


def ingest_all_documents() -> dict[str, Any]:
    settings = get_settings()
    results = []
    for path in sorted(settings.docs_path.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED:
            try:
                count = ingest_path(path)
                results.append({"source": path.relative_to(settings.docs_path).as_posix(), "chunks": count, "status": "ok"})
            except Exception as exc:
                results.append({"source": path.name, "chunks": 0, "status": "error", "error": str(exc)})
    return {"files_seen": len(results), "chunks_indexed": sum(r["chunks"] for r in results), "results": results}
