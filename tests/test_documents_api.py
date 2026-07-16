from pathlib import Path

from tests.conftest import upload_text_file

FIXTURES = Path(__file__).parent / "fixtures"


def test_upload_success_returns_id_and_chunk_count(client):
    resp = upload_text_file(client, "notes.md", "# Notes\n\nHello world, this is a test file.")
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "notes.md"
    assert body["status"] == "indexed"
    assert body["num_chunks"] >= 1
    assert body["id"]


def test_upload_unsupported_type_returns_415(client):
    resp = client.post("/documents", files={"file": ("image.png", b"\x89PNG\r\n", "image/png")})
    assert resp.status_code == 415
    assert resp.json()["error"]["code"] == "unsupported_file_type"


def test_upload_oversized_returns_413(client):
    # Default MAX_UPLOAD_MB is 10; exceed it comfortably.
    big_content = "a" * (11 * 1024 * 1024)
    resp = upload_text_file(client, "big.txt", big_content)
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "file_too_large"


def test_upload_empty_document_returns_400(client):
    resp = upload_text_file(client, "empty.txt", "   \n  ")
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "empty_document"


def test_list_documents_shows_uploaded(client):
    upload_text_file(client, "a.txt", "hello world")
    resp = client.get("/documents")
    assert resp.status_code == 200
    docs = resp.json()["documents"]
    assert len(docs) == 1
    assert docs[0]["filename"] == "a.txt"


def test_list_documents_empty_store(client):
    resp = client.get("/documents")
    assert resp.status_code == 200
    assert resp.json() == {"documents": []}


def test_delete_document_removes_it(client):
    upload_resp = upload_text_file(client, "a.txt", "hello world")
    document_id = upload_resp.json()["id"]

    delete_resp = client.delete(f"/documents/{document_id}")
    assert delete_resp.status_code == 204

    list_resp = client.get("/documents")
    assert list_resp.json() == {"documents": []}


def test_delete_unknown_document_returns_404(client):
    resp = client.delete("/documents/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_persistence_across_fresh_store(client, tmp_data_dir):
    upload_text_file(client, "a.txt", "hello world")

    from app.services.metadata import MetadataStore

    fresh_store = MetadataStore(tmp_data_dir)
    rows = fresh_store.list_documents()
    assert len(rows) == 1
    assert rows[0]["filename"] == "a.txt"


def test_upload_pdf_success(client):
    data = (FIXTURES / "sample.pdf").read_bytes()
    resp = client.post("/documents", files={"file": ("sample.pdf", data, "application/pdf")})
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "indexed"
    assert body["num_chunks"] >= 1


def test_upload_pdf_with_no_text_returns_400(client):
    data = (FIXTURES / "empty.pdf").read_bytes()
    resp = client.post("/documents", files={"file": ("empty.pdf", data, "application/pdf")})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "empty_document"


def test_upload_corrupt_pdf_returns_422(client):
    data = (FIXTURES / "corrupt.pdf").read_bytes()
    resp = client.post("/documents", files={"file": ("corrupt.pdf", data, "application/pdf")})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "extraction_failed"
