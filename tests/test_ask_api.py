from app.errors import ModelApiError
from tests.conftest import upload_text_file


def test_ask_returns_answer_and_citations(client, mock_claude):
    upload_text_file(client, "handbook.md", "Refunds are available within 30 days of purchase.")

    resp = client.post("/ask", json={"question": "What is the refund policy?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == mock_claude.complete.return_value
    assert len(body["citations"]) >= 1
    citation = body["citations"][0]
    assert citation["filename"] == "handbook.md"
    assert citation["document_id"]
    assert isinstance(citation["chunk_index"], int)


def test_ask_empty_question_returns_422(client):
    resp = client.post("/ask", json={"question": ""})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_ask_over_long_question_returns_422(client):
    resp = client.post("/ask", json={"question": "a" * 2001})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_ask_empty_corpus_returns_friendly_200(client):
    resp = client.post("/ask", json={"question": "Anything in here?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["citations"] == []
    assert "No documents have been indexed" in body["answer"]


def test_ask_model_api_error_returns_502(client, mock_claude):
    upload_text_file(client, "handbook.md", "Some content to retrieve.")
    mock_claude.complete.side_effect = ModelApiError("The Claude API request failed.")

    resp = client.post("/ask", json={"question": "What does the handbook say?"})
    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "model_api_error"
