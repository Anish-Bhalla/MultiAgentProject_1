from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=5000)
    session_id: str | None = Field(default=None, max_length=100)

    @field_validator("question")
    @classmethod
    def clean_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question cannot be blank.")
        return value


class FeedbackRequest(BaseModel):
    trace_id: str = Field(min_length=1, max_length=100)
    rating: Literal["positive", "negative"]
    category: Literal[
        "wrong_sql", "wrong_data", "wrong_retrieval", "missing_information",
        "incorrect_reasoning", "hallucination", "poor_answer", "security_issue", "other"
    ] = "other"
    comment: str = Field(default="", max_length=2000)
