# askdocs - Phases

Phases are ordered so that Phase 1 is the smallest shippable slice that delivers the core value (ask a question over text files and get a cited answer). Later phases add PDF support, auth, the web UI, and the CLI. Each phase lists a Definition of Done, a Manual test checklist, and the exact commit sequence (one commit per feature/task, Conventional Commits, in order).

Do not start a phase before the previous one is done. Within a phase, commit in the listed order.

---

## Phase 1 - Core Q&A over text files

The smallest useful product: upload `.txt`/`.md`, ask a question, get an answer with citations. Includes config, structured logging, the consistent error format, extraction (txt/md), chunking, local embeddings, Chroma persistence, SQLite metadata with the migration runner, and all data endpoints except PDF and auth.

### Definition of done
- `uv run uvicorn app.main:app` starts and serves `GET /health` -> `{"status":"ok"}`.
- Uploading a `.txt` or `.md` file returns `201` with `id`, `filename`, `num_chunks`, `status: "indexed"`, and the file is chunked, embedded, and persisted.
- Upload validation rejects unsupported types (`415`) and oversized files (`413`) server-side; empty-text files return `400 empty_document`.
- `GET /documents` lists indexed documents newest-first; `DELETE /documents/{id}` removes a document and its chunks (`204`), unknown id returns `404`.
- `POST /ask` returns `200` with a grounded `answer` and a `citations` array; empty corpus returns the friendly `200` answer with empty citations.
- All errors use the single JSON error format; no stack traces leak.
- SQLite schema is created by the migration runner from `app/migrations/001_init.sql`; `schema_migrations` records it.
- Data persists across a process restart.
- Structured JSON logs are emitted with a per-request id; secrets and document contents are never logged.
- `ruff check .`, `black --check .`, and `pytest` all pass. The Claude API is mocked in tests.

### Manual test checklist
- [x] Start the server; `curl /health` returns `{"status":"ok"}`.
- [x] Upload a small `.md` file; confirm `201` and a plausible `num_chunks`.
- [x] `GET /documents` shows the uploaded document.
- [x] Ask a question answerable from the file; confirm the answer is grounded and citations reference the uploaded file and real chunk indices.
- [x] Ask something not in the file; confirm the answer says it is not found and citations are empty or minimal (no fabrication).
- [x] Upload a `.png`; confirm `415 unsupported_file_type`.
- [x] Upload a file larger than `MAX_UPLOAD_MB`; confirm `413 file_too_large`.
- [x] `POST /ask` with `{"question": ""}`; confirm `422 validation_error`.
- [x] `POST /ask` on an empty store; confirm the friendly `200` answer with empty citations.
- [x] Delete the document; confirm `204`, then `GET /documents` is empty and `DELETE` again returns `404`.
- [x] Restart the server; confirm previously indexed data is still listed (upload one before restarting to verify).
- [x] Inspect logs: JSON lines with request ids; no document text or API key present.

### Commits
1. `build: scaffold project with pyproject, uv.lock, ruff and black config`
2. `chore: add .env.example and .gitignore`
3. `feat(config): add settings module reading environment variables`
4. `feat(logging): add structured JSON logging and request-id middleware`
5. `feat(errors): add error schema, AppError types, and exception handlers`
6. `feat(app): create FastAPI app and register health route`
7. `feat(metadata): add SQLite store and migration runner with 001_init`
8. `feat(extraction): extract text from txt and md uploads`
9. `feat(chunking): add fixed-size chunker with overlap`
10. `feat(embeddings): configure local Chroma default embedding function`
11. `feat(vectorstore): wrap Chroma add, query, and delete`
12. `feat(documents): add upload endpoint with server-side validation`
13. `feat(documents): add list and delete endpoints`
14. `feat(claude): add Anthropic client wrapper`
15. `feat(ask): compose answer with citations from retrieved chunks`
16. `test(phase1): add unit and integration tests with mocked Claude`
17. `docs: add run and test instructions to README`

---

## Phase 2 - PDF support

Add PDF extraction to the existing upload pipeline.

### Definition of done
- Uploading a text-bearing `.pdf` indexes it like other types; `content_type` is `application/pdf`.
- A PDF with no extractable text returns `400 empty_document` and is not left as an `indexed` row.
- A corrupt/unreadable PDF returns `422 extraction_failed`.
- Tests cover PDF extraction (with a small fixture PDF) and the no-text case.
- Lint, format, and tests pass.

### Manual test checklist
- [x] Upload a normal text PDF; confirm `201` and sensible `num_chunks`.
- [x] Ask a question answerable from the PDF; confirm grounded answer and citations.
- [x] Upload an image-only/scanned PDF; confirm `400 empty_document`.
- [x] Upload a truncated/corrupt PDF; confirm `422 extraction_failed`.

### Commits
1. `build: add pypdf dependency`
2. `feat(extraction): extract text from pdf uploads`
3. `test(extraction): cover pdf extraction and empty-text pdf`

---

## Phase 3 - Optional API-key authentication

Gate data routes behind `X-API-Key` when `API_KEY` is configured.

### Definition of done
- With `API_KEY` unset, all routes behave as before (open).
- With `API_KEY` set, `POST /documents`, `GET /documents`, `DELETE /documents/{id}`, and `POST /ask` require a matching `X-API-Key` header; missing/wrong returns `401 unauthorized`. `GET /health` stays open.
- Key comparison is constant-time. The key is never logged.
- Protected routes are documented (OpenAPI reflects the header dependency; `docs/api-contracts.md` already lists them).
- Tests cover: open when unset, allowed with correct key, `401` with missing/wrong key.
- Lint, format, and tests pass.

### Manual test checklist
- [x] With `API_KEY` unset, all endpoints work with no header.
- [x] Set `API_KEY`; requests without `X-API-Key` return `401`.
- [x] Requests with a wrong key return `401`.
- [x] Requests with the correct key succeed.
- [x] `GET /health` works without a key even when `API_KEY` is set.
- [x] Confirm the key does not appear in logs.

### Commits
1. `feat(auth): add optional api-key dependency for data routes`
2. `test(auth): cover open, authorized, and rejected requests`

---

## Phase 4 - Minimal web UI

A single static page served by the app: upload, ask, and view answers with citation chips.

### Definition of done
- `GET /` serves `web/index.html`; `web/app.js` and `web/styles.css` load as static assets.
- The page can upload a file, list documents, delete a document, ask a question, and render the answer with citation chips, all against the existing API.
- Loading, empty, and error states are implemented for upload, list, ask, and answer, per `docs/design.md`.
- Accessibility per `docs/design.md`: labels, visible focus, `aria-live`/`role` regions, keyboard operability, AA contrast in light and dark.
- When auth is enabled, the UI prompts for and sends the `X-API-Key` header (stored in memory or `localStorage`), and handles `401` by re-prompting.
- No external CDN assets or web fonts.

### Manual test checklist
- [x] Load `/`; upload a file via the form; see it appear in the list.
- [x] Ask a question; see the loading state, then the answer and citation chips.
- [x] Activate a citation chip with mouse and with keyboard; see the snippet.
- [x] Delete a document from the list; confirm it disappears.
- [x] Trigger an error (unsupported file); see the inline error with `role="alert"`.
- [x] Ask with an empty question; see inline validation, no request sent.
- [x] Ask on an empty corpus; see the friendly answer, not an error style.
- [x] Tab through the page; focus is always visible and order is logical.
- [x] Toggle OS dark mode; confirm both themes are legible and pass contrast.
- [x] Check at 375px width and 200% zoom; no horizontal body scroll.

### Commits
1. `feat(web): add static single-page ui shell and styles`
2. `feat(web): wire upload, list, delete, and ask to the api`
3. `feat(web): add loading, empty, and error states with citation chips`
4. `feat(app): mount static web assets`

---

## Phase 5 - CLI

A small CLI client over HTTP: `add`, `list`, `delete`, `ask`.

### Definition of done
- `uv run python -m cli.askdocs_cli <command>` supports:
  - `add <path>` - upload a file, print id and chunk count.
  - `list` - print indexed documents.
  - `delete <id>` - delete a document.
  - `ask "<question>"` - print the answer and its citations.
- Base URL comes from `--base-url` or `ASKDOCS_URL` (default `http://127.0.0.1:8000`); API key from `--api-key` or `ASKDOCS_API_KEY`.
- Errors from the API are printed as readable messages (using `error.message`), and the process exits non-zero on failure.
- Tests cover argument parsing and request building against a mocked HTTP layer.
- Lint, format, and tests pass.

### Manual test checklist
- [x] `add` a file; confirm printed id and chunk count, and that it appears in `list`.
- [x] `ask` a question; confirm answer and citations print readably.
- [x] `delete` the id; confirm it is gone from `list`.
- [x] Point at a down server; confirm a friendly error and non-zero exit.
- [x] With auth enabled, confirm `--api-key`/`ASKDOCS_API_KEY` is required and used.

### Commits
1. `build: add httpx dependency for cli`
2. `feat(cli): add add, list, delete, and ask commands`
3. `test(cli): cover argument parsing and request building`

---

## Phase verification (run after every phase)

- [x] Run the API (`uv run uvicorn app.main:app`) and confirm it starts without errors.
- [x] Run the full test suite (`uv run pytest`); all pass with the Claude API mocked.
- [x] Run `uv run ruff check .` and `uv run black --check .`; both clean.
- [x] Check logs during a manual run: structured JSON, request ids present, no document text or secrets.
- [x] Unhappy paths:
  - [x] Unsupported file type -> `415 unsupported_file_type`.
  - [x] Oversized file -> `413 file_too_large`.
  - [x] Empty question -> `422 validation_error`.
  - [x] Question with no documents indexed -> friendly `200`, empty citations.
  - [x] Missing API key when auth enabled -> `401 unauthorized`.
  - [x] Claude API unreachable / network down (simulate) -> `502 model_api_error`, friendly message, detail logged.
  - [x] Very long question (> 2000 chars) -> `422 validation_error`.
- [x] Empty states:
  - [x] `GET /documents` on empty store -> `{"documents": []}`.
  - [x] Web UI (if built) shows the empty-documents message.
- [x] Persistence: restart the process; previously indexed documents and answers are still available.

## Backlog

(Empty. Add out-of-scope or deferred items here with a one-line rationale as they are discovered. Do not implement backlog items without moving them into a phase first.)
