"""Request/response models for the /documents routes."""

from pydantic import BaseModel


class UploadResult(BaseModel):
    id: str
    filename: str
    num_chunks: int
    status: str


class DocumentOut(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    num_chunks: int
    status: str
    created_at: str


class DocumentListOut(BaseModel):
    documents: list[DocumentOut]
