"""POST /documents, GET /documents, DELETE /documents/{id}."""

import logging
import os
import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, UploadFile

from app.config import Settings, get_settings
from app.deps import get_metadata_store, get_vector_store, require_api_key
from app.errors import (
    EmptyDocumentError,
    FileTooLargeError,
    NotFoundError,
    UnsupportedFileTypeError,
)
from app.schemas.documents import DocumentListOut, DocumentOut, UploadResult
from app.services.chunking import chunk_text
from app.services.extraction import EXTENSION_TO_CONTENT_TYPE, extract_text
from app.services.metadata import MetadataStore
from app.services.vectorstore import VectorStore

router = APIRouter(dependencies=[Depends(require_api_key)])
logger = logging.getLogger("askdocs.documents")

_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


def sanitize_filename(raw_name: str) -> str:
    """Strip directory components and unsafe characters; never used as a filesystem path."""
    name = os.path.basename(raw_name or "upload")
    name = _SAFE_CHARS.sub("_", name).strip("._") or "upload"
    return name[:255]


def _resolve_content_type(filename: str, declared_content_type: str | None) -> str:
    ext = os.path.splitext(filename)[1].lower()
    expected = EXTENSION_TO_CONTENT_TYPE.get(ext)
    if expected is None:
        raise UnsupportedFileTypeError("Only .txt, .md, and .pdf files are supported.")
    return expected


@router.post("/documents", response_model=UploadResult, status_code=201)
async def upload_document(
    file: UploadFile,
    settings: Settings = Depends(get_settings),
    metadata_store: MetadataStore = Depends(get_metadata_store),
    vector_store: VectorStore = Depends(get_vector_store),
) -> UploadResult:
    filename = sanitize_filename(file.filename or "upload")
    content_type = _resolve_content_type(filename, file.content_type)

    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise FileTooLargeError(f"File exceeds the {settings.max_upload_mb}MB upload limit.")

    text = extract_text(data, content_type)
    if not text.strip():
        raise EmptyDocumentError("The file contained no extractable text.")

    chunks = chunk_text(text)
    document_id = uuid.uuid4().hex
    created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    vector_store.add_chunks(document_id, filename, chunks)
    metadata_store.insert_document(
        document_id=document_id,
        filename=filename,
        content_type=content_type,
        size_bytes=len(data),
        num_chunks=len(chunks),
        status="indexed",
        error=None,
        created_at=created_at,
    )
    logger.info(
        "document_indexed",
        extra={
            "document_id": document_id,
            "document_filename": filename,
            "num_chunks": len(chunks),
        },
    )
    return UploadResult(id=document_id, filename=filename, num_chunks=len(chunks), status="indexed")


@router.get("/documents", response_model=DocumentListOut)
def list_documents(metadata_store: MetadataStore = Depends(get_metadata_store)) -> DocumentListOut:
    rows = metadata_store.list_documents()
    return DocumentListOut(documents=[DocumentOut(**dict(row)) for row in rows])


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    metadata_store: MetadataStore = Depends(get_metadata_store),
    vector_store: VectorStore = Depends(get_vector_store),
) -> None:
    existing = metadata_store.get_document(document_id)
    if existing is None:
        raise NotFoundError("No document with that id exists.")
    vector_store.delete_document(document_id)
    metadata_store.delete_document(document_id)
    logger.info("document_deleted", extra={"document_id": document_id})
