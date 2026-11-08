"""main(): argument wiring, the API key header, and friendly exits on errors."""

import httpx
import pytest

from cli import askdocs_cli


@pytest.fixture
def server(monkeypatch):
    calls = []

    def handler(request):
        calls.append((request.method, request.url.path, request.headers.get("X-API-Key")))
        if request.url.path == "/documents" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "documents": [
                        {"id": "d1", "filename": "a.md", "num_chunks": 2, "status": "indexed"}
                    ]
                },
            )
        if request.url.path == "/documents" and request.method == "POST":
            return httpx.Response(201, json={"id": "d1", "filename": "a.md", "num_chunks": 2})
        if request.method == "DELETE":
            return httpx.Response(
                404, json={"error": {"code": "not_found", "message": "Document not found."}}
            )
        if request.url.path == "/ask":
            return httpx.Response(
                200,
                json={
                    "answer": "Thirty days.",
                    "citations": [
                        {"filename": "a.md", "chunk_index": 0, "snippet": "Refunds within 30 days"}
                    ],
                },
            )
        return httpx.Response(500)

    real = httpx.Client
    monkeypatch.setattr(
        askdocs_cli.httpx, "Client", lambda **kw: real(transport=httpx.MockTransport(handler), **kw)
    )
    return calls


def test_list_add_and_ask_print_readably(server, tmp_path, capsys):
    doc = tmp_path / "a.md"
    doc.write_text("Refunds within 30 days")
    askdocs_cli.main(["--api-key", "k", "list"])
    askdocs_cli.main(["--api-key", "k", "add", str(doc)])
    askdocs_cli.main(["--api-key", "k", "ask", "refund window?"])

    out = capsys.readouterr().out
    assert "d1  a.md  chunks=2  status=indexed" in out
    assert "Indexed a.md (id=d1, chunks=2)." in out
    assert "Thirty days." in out and "a.md #0" in out
    assert {key for _, _, key in server} == {"k"}


def test_server_errors_print_the_message_and_exit_1(server, capsys):
    with pytest.raises(SystemExit) as exit_info:
        askdocs_cli.main(["delete", "missing"])
    assert exit_info.value.code == 1
    assert "Document not found." in capsys.readouterr().err


def test_a_missing_file_is_a_friendly_error(server, tmp_path, capsys):
    with pytest.raises(SystemExit) as exit_info:
        askdocs_cli.main(["add", str(tmp_path / "nope.md")])
    assert exit_info.value.code == 1
