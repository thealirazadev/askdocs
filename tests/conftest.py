"""Shared pytest fixtures: temp DATA_DIR, FastAPI TestClient, and a mocked Claude client."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.deps import reset_store_caches
from app.main import app
from app.routers.ask import get_claude_client


@pytest.fixture
def tmp_data_dir(tmp_path):
    return str(tmp_path / "data")


@pytest.fixture
def mock_claude():
    client = MagicMock()
    client.complete.return_value = "This is a mocked answer grounded in the retrieved passages."
    return client


@pytest.fixture
def client(tmp_data_dir, mock_claude):
    test_settings = Settings(
        anthropic_api_key="test-key",
        data_dir=tmp_data_dir,
        api_key="",
    )

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_claude_client] = lambda: mock_claude
    reset_store_caches()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    reset_store_caches()


def upload_text_file(
    client: TestClient, filename: str, content: str, content_type: str = "text/plain"
):
    return client.post(
        "/documents", files={"file": (filename, content.encode("utf-8"), content_type)}
    )
