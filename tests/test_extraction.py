from pathlib import Path

import pytest

from app.errors import ExtractionFailedError
from app.services.extraction import extract_text

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_plain_text():
    assert extract_text(b"hello world", "text/plain") == "hello world"


def test_extract_markdown_text():
    assert extract_text(b"# Title\n\nBody", "text/markdown") == "# Title\n\nBody"


def test_extract_invalid_utf8_raises_extraction_failed():
    with pytest.raises(ExtractionFailedError):
        extract_text(b"\xff\xfe\x00\x01", "text/plain")


def test_extract_unsupported_content_type_raises():
    with pytest.raises(ExtractionFailedError):
        extract_text(b"data", "application/zip")


def test_extract_pdf_text():
    data = (FIXTURES / "sample.pdf").read_bytes()
    text = extract_text(data, "application/pdf")
    assert "Hello PDF world" in text


def test_extract_pdf_with_no_text_yields_blank():
    data = (FIXTURES / "empty.pdf").read_bytes()
    text = extract_text(data, "application/pdf")
    assert text.strip() == ""


def test_extract_corrupt_pdf_raises_extraction_failed():
    data = (FIXTURES / "corrupt.pdf").read_bytes()
    with pytest.raises(ExtractionFailedError):
        extract_text(data, "application/pdf")
