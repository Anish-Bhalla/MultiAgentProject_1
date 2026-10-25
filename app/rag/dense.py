"""Optional dense retrieval using SentenceTransformers + Chroma. Install requirements-dense.txt."""
from __future__ import annotations
from typing import Any
from app.config import get_settings

_COLLECTION = "enterprise_document_chunks"
_model = None
_client = None
_collection_obj = None


def _resources():
    global _model, _client, _collection_obj
    if _model is None:
        from sentence_transformers import SentenceTransformer
        import chromadb
        settings = get_settings()
        _model = SentenceTransformer(settings.embedding_model)
        _client = chromadb.PersistentClient(path=settings.chroma_dir)
        _collection_obj = _client.get_or_create_collection(name=_COLLECTION, metadata={"hnsw:space": "cosine"})
    return _model, _collection_obj


def index_chunks(source: str, chunks: list[dict[str, Any]]) -> None:
    model, collection = _resources()
    # Delete-and-replace by source so repeated ingestion is idempotent.
    existing = collection.get(where={"source": source}, include=[])
    if existing.get("ids"):
        collection.delete(ids=existing["ids"])
    if not chunks:
        return
    ids = [f"{source}:{i}:{chunk['metadata'].get('content_hash','')}" for i, chunk in enumerate(chunks)]
    docs = [chunk["text"] for chunk in chunks]
    embeddings = model.encode(docs, normalize_embeddings=True).tolist()
    metadatas = []
    for i, chunk in enumerate(chunks):
        md = {k: ("" if v is None else v) for k, v in chunk["metadata"].items() if isinstance(v, (str, int, float)) or v is None}
        md["source"] = source
        md["local_chunk_index"] = i
        metadatas.append(md)
    collection.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas)


def search_dense(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    model, collection = _resources()
    if collection.count() == 0:
        return []
    vec = model.encode([query], normalize_embeddings=True).tolist()
    result = collection.query(query_embeddings=vec, n_results=max(1, min(top_k, 20)), include=["documents", "metadatas", "distances"])
    out = []
    ids = (result.get("ids") or [[]])[0]
    docs = (result.get("documents") or [[]])[0]
    metadata_rows = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]
    for idx, doc in enumerate(docs):
        md = metadata_rows[idx] or {}
        page = md.get("page")
        source = str(md.get("source", "unknown"))
        citation = source + (f", page {page}" if page not in (None, "") else "")
        out.append({"chunk_id": ids[idx], "source": source, "page": page or None, "citation": citation,
                    "text": doc, "score": round(1 - float(distances[idx]), 4), "metadata": md, "retrieval_method": "dense"})
    return out
