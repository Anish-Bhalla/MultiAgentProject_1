from __future__ import annotations
import json
import re
from typing import Any
from rank_bm25 import BM25Okapi
from app.config import get_settings
from app.database import connect_state, utc_now


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+|₹\d+(?:\.\d+)?|%", text.lower())


def replace_source_chunks(source: str, chunks: list[dict[str, Any]]) -> int:
    with connect_state() as conn:
        conn.execute("DELETE FROM document_chunks WHERE source = ?", (source,))
        for idx, chunk in enumerate(chunks):
            metadata = dict(chunk.get("metadata", {}))
            page = metadata.get("page")
            # Use the same stable identity as the optional dense index so hybrid RRF
            # can merge lexical and semantic hits for the same underlying chunk.
            chunk_id = f"{source}:{idx}:{metadata.get('content_hash', '')}"
            conn.execute(
                "INSERT INTO document_chunks(chunk_id,source,page,chunk_index,text,metadata_json,created_at) VALUES(?,?,?,?,?,?,?)",
                (chunk_id, source, page, idx, chunk["text"], json.dumps(metadata, ensure_ascii=False), utc_now()),
            )
    return len(chunks)


def all_chunks() -> list[dict[str, Any]]:
    with connect_state() as conn:
        rows = conn.execute("SELECT chunk_id,source,page,chunk_index,text,metadata_json FROM document_chunks ORDER BY source, chunk_index").fetchall()
    items = []
    for row in rows:
        d = dict(row)
        d["metadata"] = json.loads(d.pop("metadata_json"))
        items.append(d)
    return items


def list_documents() -> list[dict[str, Any]]:
    with connect_state() as conn:
        rows = conn.execute(
            "SELECT source, COUNT(*) AS chunks, MAX(created_at) AS indexed_at FROM document_chunks GROUP BY source ORDER BY source"
        ).fetchall()
    return [dict(row) for row in rows]


def search_bm25(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    chunks = all_chunks()
    if not chunks:
        return []
    corpus = [tokenize(item["text"]) for item in chunks]
    if not any(corpus):
        return []
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
    out = []
    for idx, score in ranked[: max(1, min(top_k, 20))]:
        if float(score) <= 0:
            continue
        item = chunks[idx]
        meta = item["metadata"]
        source = item["source"]
        citation = f"{source}" + (f", page {item['page']}" if item.get("page") else "")
        out.append({
            "chunk_id": item["chunk_id"], "source": source, "page": item.get("page"),
            "citation": citation, "text": item["text"], "score": round(float(score), 4),
            "metadata": meta, "retrieval_method": "bm25",
        })
    return out


def search_documents(query: str, top_k: int = 5) -> dict[str, Any]:
    settings = get_settings()
    mode = settings.rag_retrieval_mode.lower()
    if mode in {"dense", "hybrid"}:
        try:
            from app.rag.dense import search_dense
            dense = search_dense(query, top_k)
            if mode == "dense":
                return {"query": query, "results": dense, "retrieval_mode": "dense"}
            lexical = search_bm25(query, top_k)
            fused = reciprocal_rank_fusion([dense, lexical], top_k)
            return {"query": query, "results": fused, "retrieval_mode": "hybrid_rrf"}
        except Exception as exc:
            lexical = search_bm25(query, top_k)
            return {"query": query, "results": lexical, "retrieval_mode": "bm25_fallback", "warning": f"Dense retrieval unavailable: {exc}"}
    return {"query": query, "results": search_bm25(query, top_k), "retrieval_mode": "bm25"}


def reciprocal_rank_fusion(result_lists: list[list[dict[str, Any]]], top_k: int) -> list[dict[str, Any]]:
    rank_scores: dict[str, float] = {}
    representatives: dict[str, dict[str, Any]] = {}
    for results in result_lists:
        for rank, item in enumerate(results, start=1):
            key = item["chunk_id"]
            rank_scores[key] = rank_scores.get(key, 0.0) + 1.0 / (60 + rank)
            representatives[key] = item
    ordered = sorted(rank_scores, key=rank_scores.get, reverse=True)[:top_k]
    final = []
    for key in ordered:
        row = dict(representatives[key])
        row["score"] = round(rank_scores[key], 6)
        row["retrieval_method"] = "rrf"
        final.append(row)
    return final
