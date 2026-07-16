import json

import httpx
import pytest

from cli.askdocs_cli import build_parser, cmd_add, cmd_ask, cmd_delete, cmd_list


def test_parser_defaults():
    parser = build_parser()
    args = parser.parse_args(["list"])
    assert args.base_url == "http://127.0.0.1:8000"
    assert args.api_key == ""
    assert args.command == "list"


def test_parser_add_requires_path():
    parser = build_parser()
    args = parser.parse_args(["add", "notes.txt"])
    assert args.command == "add"
    assert args.path == "notes.txt"


def test_parser_ask_requires_question():
    parser = build_parser()
    args = parser.parse_args(["ask", "What is this?"])
    assert args.question == "What is this?"


def test_parser_delete_requires_id():
    parser = build_parser()
    args = parser.parse_args(["delete", "abc123"])
    assert args.id == "abc123"


def _mock_client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.Client(base_url="http://testserver", transport=transport)


def test_cmd_add_uploads_file(tmp_path, capsys):
    path = tmp_path / "notes.txt"
    path.write_text("hello world")

    def handler(request):
        assert request.url.path == "/documents"
        return httpx.Response(
            201, json={"id": "abc", "filename": "notes.txt", "num_chunks": 1, "status": "indexed"}
        )

    client = _mock_client(handler)
    cmd_add(client, str(path))
    out = capsys.readouterr().out
    assert "notes.txt" in out
    assert "abc" in out


def test_cmd_list_prints_documents(capsys):
    def handler(request):
        assert request.url.path == "/documents"
        return httpx.Response(
            200,
            json={
                "documents": [
                    {"id": "abc", "filename": "a.txt", "num_chunks": 2, "status": "indexed"}
                ]
            },
        )

    client = _mock_client(handler)
    cmd_list(client)
    out = capsys.readouterr().out
    assert "a.txt" in out


def test_cmd_delete(capsys):
    def handler(request):
        assert request.url.path == "/documents/abc"
        assert request.method == "DELETE"
        return httpx.Response(204)

    client = _mock_client(handler)
    cmd_delete(client, "abc")
    out = capsys.readouterr().out
    assert "abc" in out


def test_cmd_ask_prints_answer_and_citations(capsys):
    def handler(request):
        assert request.url.path == "/ask"
        body = json.loads(request.content)
        assert body["question"] == "What is this?"
        return httpx.Response(
            200,
            json={
                "answer": "It is a test.",
                "citations": [
                    {
                        "document_id": "abc",
                        "filename": "a.txt",
                        "chunk_index": 0,
                        "snippet": "test snippet",
                        "score": 0.9,
                    }
                ],
            },
        )

    client = _mock_client(handler)
    cmd_ask(client, "What is this?")
    out = capsys.readouterr().out
    assert "It is a test." in out
    assert "a.txt" in out


def test_cmd_ask_raises_on_error_response():
    def handler(request):
        return httpx.Response(422, json={"error": {"code": "validation_error", "message": "bad"}})

    client = _mock_client(handler)
    with pytest.raises(httpx.HTTPStatusError):
        cmd_ask(client, "")
