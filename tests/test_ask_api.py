import re

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


def _two_documents(client):
    upload_text_file(client, "refunds.md", "Refunds are available within 30 days of purchase.")
    upload_text_file(client, "hello.md", "Hello world, this file is about greetings.")


def test_citations_are_only_the_passages_the_answer_used(client, mock_claude):
    _two_documents(client)

    def answer(system, user):
        number = re.search(r"\[(\d+)\] \(from refunds\.md", user).group(1)
        return f"Refunds are available within 30 days.\nSOURCES: {number}"

    mock_claude.complete.side_effect = answer

    body = client.post("/ask", json={"question": "What is the refund window?"}).json()

    assert body["answer"] == "Refunds are available within 30 days."
    assert [c["filename"] for c in body["citations"]] == ["refunds.md"]


def test_an_answer_with_no_sources_has_no_citations(client, mock_claude):
    _two_documents(client)
    mock_claude.complete.return_value = "The documents do not say.\nSOURCES: none"

    body = client.post("/ask", json={"question": "What is the CEO's name?"}).json()

    assert body == {"answer": "The documents do not say.", "citations": []}


def test_a_missing_or_bad_sources_line_keeps_every_passage(client, mock_claude):
    _two_documents(client)
    for reply in ("An answer without the line.", "An answer.\nSOURCES: 9"):
        mock_claude.complete.return_value = reply
        body = client.post("/ask", json={"question": "Refunds or greetings?"}).json()
        assert len(body["citations"]) == 2
        assert "SOURCES" not in body["answer"]
