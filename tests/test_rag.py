from app.agents.planner import heuristic_plan
from app.rag.ingestion import chunk_text
from app.rag.store import reciprocal_rank_fusion


def test_chunk_text_respects_size_and_keeps_content():
    text = ("This is a useful sentence. " * 80).strip()
    chunks = chunk_text(text, chunk_chars=400, overlap=50)
    assert len(chunks) > 1
    assert all(len(chunk) <= 430 for chunk in chunks)
    assert "useful sentence" in " ".join(chunks)


def test_planner_selects_multiple_agents_for_mixed_question():
    plan = heuristic_plan("Why did revenue decline and what does management say about demand?")
    assert plan["use_sql"] is True
    assert plan["use_rag"] is True
    assert "sql" in plan["tasks"] and "rag" in plan["tasks"]


def test_rrf_merges_lexical_and_dense_results():
    a = {"chunk_id": "a", "text": "shared", "source": "a.md", "score": 0.9}
    b = {"chunk_id": "b", "text": "other", "source": "b.md", "score": 0.8}
    fused = reciprocal_rank_fusion([[a, b], [a]], 2)
    assert fused[0]["chunk_id"] == "a"
    assert fused[0]["retrieval_method"] == "rrf"
