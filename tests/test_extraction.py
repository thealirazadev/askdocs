import pytest

from app.errors import ExtractionFailedError
from app.services.extraction import extract_text


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
