# askdocs - API Contracts

Base URL: `http://127.0.0.1:8000`. All request and response bodies are JSON except document upload, which is `multipart/form-data`. All timestamps are ISO-8601 UTC strings.

## Authentication

- Auth is optional and controlled by the `API_KEY` environment variable.
- If `API_KEY` is **unset**: all routes are open (local convenience default).
- If `API_KEY` is **set**: the protected routes below require an `X-API-Key: <key>` request header matching `API_KEY`. A missing or wrong key returns `401` with `code: "unauthorized"`. Key comparison is constant-time.

Protected routes (require `X-API-Key` when `API_KEY` is set):
- `POST /documents`
- `GET /documents`
- `DELETE /documents/{id}`
- `POST /ask`

Open routes (never require a key):
- `GET /health`
- Static web assets under `/` (Phase 4)

## Error format

Every non-2xx response uses this exact shape:

```json
{
  "error": {
    "code": "string_snake_case",
    "message": "Human-readable, safe to display."
  }
}
```

Defined `code` values and typical HTTP status:

| code                   | status | meaning                                             |
|------------------------|--------|-----------------------------------------------------|
| `validation_error`     | 422    | Malformed body or failed field validation.          |
| `unauthorized`         | 401    | Missing or invalid `X-API-Key` (when auth enabled). |
| `not_found`            | 404    | Resource id does not exist.                         |
| `unsupported_file_type`| 415    | Upload is not `.txt`, `.md`, or `.pdf`.             |
| `file_too_large`       | 413    | Upload exceeds `MAX_UPLOAD_MB`.                      |
| `empty_document`       | 400    | File contained no extractable text.                 |
| `no_documents_indexed` | 200    | Not an error status; see `/ask` empty-corpus note.  |
| `extraction_failed`    | 422    | File could not be parsed.                           |
| `embedding_failed`     | 503    | Embedding model failed.                             |
| `vector_store_error`   | 503    | Chroma add/query/delete failed.                     |
| `model_api_error`      | 502    | Claude API call failed.                             |
| `internal_error`       | 500    | Unhandled server error.                             |

Stack traces, file paths, SQL, and secrets never appear in `message`.

---

## GET /health

Liveness check. Always open.

- Request: none.
- Response `200`:

```json
{ "status": "ok" }
```

---

## POST /documents

Upload and index a document. `multipart/form-data`.

- Request: form field `file` (the document). Allowed types: `.txt` (`text/plain`), `.md` (`text/markdown`), `.pdf` (`application/pdf`). Max size `MAX_UPLOAD_MB` (default 10 MB).
- Success `201`:

```json
{
  "id": "3f1c9a2b7d4e4f0a8c1e5b6d7a2f9c00",
  "filename": "handbook.md",
  "num_chunks": 42,
  "status": "indexed"
}
```

- Errors:
  - `415 unsupported_file_type` - extension/content type not allowed.
  - `413 file_too_large` - exceeds the size limit.
  - `400 empty_document` - no extractable text (e.g. an image-only PDF).
  - `422 extraction_failed` - file could not be parsed.
  - `503 embedding_failed` / `503 vector_store_error` - indexing failed; no partial document is left listed as `indexed`.
  - `401 unauthorized` - when auth is enabled and the key is missing/wrong.

Example:

```bash
curl -F "file=@handbook.md" http://127.0.0.1:8000/documents
# with auth:
curl -H "X-API-Key: $API_KEY" -F "file=@handbook.md" http://127.0.0.1:8000/documents
```

---

## GET /documents

List all indexed documents, newest first.

- Request: none.
- Success `200`:

```json
{
  "documents": [
    {
      "id": "3f1c9a2b7d4e4f0a8c1e5b6d7a2f9c00",
      "filename": "handbook.md",
      "content_type": "text/markdown",
      "size_bytes": 18422,
      "num_chunks": 42,
      "status": "indexed",
      "created_at": "2026-07-15T12:00:00Z"
    }
  ]
}
```

- Empty store returns `200` with `{ "documents": [] }`.
- Error: `401 unauthorized` when auth enabled.

---

## DELETE /documents/{id}

Delete a document and all of its chunks/embeddings.

- Path param: `id` - the document id.
- Success `204`: empty body.
- Errors:
  - `404 not_found` - unknown id.
  - `401 unauthorized` - when auth enabled.

Deletion removes the SQLite row and all Chroma records whose `document_id` matches. It is idempotent from the client's perspective only in that a second delete of the same id returns `404`.

---

## POST /ask

Ask a question over the indexed corpus.

- Request body:

```json
{
  "question": "What is the refund policy?",
  "top_k": 5
}
```

  - `question` (string, required): 1 to 2000 characters after trimming. Empty/whitespace-only is `422 validation_error`. Longer than 2000 chars is `422 validation_error`.
  - `top_k` (int, optional): 1 to 20; defaults to the `TOP_K` setting (default 5). Out-of-range is `422`.

- Success `200`:

```json
{
  "answer": "Refunds are available within 30 days of purchase...",
  "citations": [
    {
      "document_id": "3f1c9a2b7d4e4f0a8c1e5b6d7a2f9c00",
      "filename": "handbook.md",
      "chunk_index": 12,
      "snippet": "...customers may request a refund within 30 days...",
      "score": 0.82
    }
  ]
}
```

  - `answer` (string): plain text, grounded in the retrieved chunks.
  - `citations` (array): each citation references one document (`document_id`, `filename`) and one passage (`chunk_index`, `snippet`, `score`). `score` is a relevance value in `[0, 1]` derived from the vector-store distance (higher is more relevant). The array may be empty when the answer is that the documents do not contain the information.

- Empty corpus: if no documents are indexed, respond `200` with a friendly answer and empty citations:

```json
{
  "answer": "No documents have been indexed yet. Upload a document before asking a question.",
  "citations": []
}
```

  This is intentionally a `200`, not an error, so clients render it as a normal answer. (`no_documents_indexed` exists as a machine hint if a client prefers to special-case it, but the transport status is `200`.)

- Errors:
  - `422 validation_error` - empty, missing, or over-long `question`; bad `top_k`.
  - `502 model_api_error` - the Claude API call failed.
  - `503 vector_store_error` / `503 embedding_failed` - retrieval failed.
  - `401 unauthorized` - when auth enabled.

Example:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the refund policy?"}'
```

---

## Status code summary

| Route                     | Success | Common errors                                             |
|---------------------------|---------|-----------------------------------------------------------|
| `GET /health`             | 200     | -                                                         |
| `POST /documents`         | 201     | 400, 413, 415, 422, 401, 503                              |
| `GET /documents`          | 200     | 401                                                      |
| `DELETE /documents/{id}`  | 204     | 404, 401                                                 |
| `POST /ask`               | 200     | 422, 401, 502, 503                                       |

All error bodies use the single error format above. Every response includes an `X-Request-ID` header for log correlation.
