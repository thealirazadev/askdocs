"""Extract plain text from uploaded file bytes, by content type.

Raises app.errors.ExtractionFailedError for unreadable/corrupt files. Callers are responsible
for rejecting empty extracted text (app.errors.EmptyDocumentError) since that check is shared
across file types.
"""

from app.errors import ExtractionFailedError

TEXT_CONTENT_TYPES = {"text/plain", "text/markdown"}
PDF_CONTENT_TYPE = "application/pdf"
SUPPORTED_CONTENT_TYPES = TEXT_CONTENT_TYPES | {PDF_CONTENT_TYPE}

EXTENSION_TO_CONTENT_TYPE = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
}


def extract_text(data: bytes, content_type: str) -> str:
    if content_type in TEXT_CONTENT_TYPES:
        return _extract_plain_text(data)
    if content_type == PDF_CONTENT_TYPE:
        return _extract_pdf_text(data)
    raise ExtractionFailedError(f"Cannot extract text from content type {content_type!r}.")


def _extract_plain_text(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExtractionFailedError("The file is not valid UTF-8 text.") from exc


def _extract_pdf_text(data: bytes) -> str:
    import io

    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except (PdfReadError, ValueError, KeyError) as exc:
        raise ExtractionFailedError("The PDF could not be parsed.") from exc
    return "\n".join(pages)
