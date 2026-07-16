import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.deps import reset_store_caches
from app.main import app
from app.routers.ask import get_claude_client


@pytest.fixture
def auth_client(tmp_data_dir, mock_claude):
    test_settings = Settings(
        anthropic_api_key="test-key",
        data_dir=tmp_data_dir,
        api_key="secret-key",
    )

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_claude_client] = lambda: mock_claude
    reset_store_caches()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    reset_store_caches()


def test_open_when_api_key_unset(client):
    resp = client.get("/documents")
    assert resp.status_code == 200


def test_health_open_even_when_api_key_set(auth_client):
    resp = auth_client.get("/health")
    assert resp.status_code == 200


def test_missing_key_returns_401(auth_client):
    resp = auth_client.get("/documents")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_wrong_key_returns_401(auth_client):
    resp = auth_client.get("/documents", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "unauthorized"


def test_correct_key_succeeds(auth_client):
    resp = auth_client.get("/documents", headers={"X-API-Key": "secret-key"})
    assert resp.status_code == 200


def test_ask_requires_key(auth_client):
    resp = auth_client.post("/ask", json={"question": "hello"})
    assert resp.status_code == 401


def test_ask_with_correct_key_succeeds(auth_client):
    resp = auth_client.post("/ask", json={"question": "hello"}, headers={"X-API-Key": "secret-key"})
    assert resp.status_code == 200
