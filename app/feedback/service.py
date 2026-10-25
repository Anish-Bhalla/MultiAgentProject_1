"""Feedback persistence service. Review records before turning them into evaluation labels."""
from app.database import get_trace, list_feedback, save_feedback


def record_feedback(trace_id: str, rating: str, category: str, comment: str) -> int:
    if get_trace(trace_id) is None:
        raise LookupError("Trace not found")
    return save_feedback(trace_id, rating, category, comment)


def recent_feedback(limit: int = 100) -> list[dict]:
    return list_feedback(limit)
