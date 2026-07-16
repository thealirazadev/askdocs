"""Request/response models for POST /ask."""

from pydantic import BaseModel, Field, field_validator


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def _question_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must not be blank")
        return stripped


class Citation(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    snippet: str
    score: float


class AskResponse(BaseModel):
    answer: str
    citations: list[Citation]
