# askdocs - Launch Checklist

Unchecked skeleton to complete before treating an askdocs instance as production-ready. Check each item off only when verified.

## Configuration and secrets
- [ ] Production environment variables set (not the `.env.example` dummies): `ANTHROPIC_API_KEY`, `DATA_DIR`, `CLAUDE_MODEL`.
- [ ] `.env` is git-ignored and not committed; no secret appears in the repo history.
- [ ] `API_KEY` is set to a strong value if the instance is reachable by anyone other than the operator.
- [ ] `DATA_DIR` points at a persistent, backed-up location with adequate disk space.
- [ ] `MAX_UPLOAD_MB`, `TOP_K`, and `LOG_LEVEL` reviewed and set appropriately for production.

## Application behavior
- [ ] Debug/reload disabled: run Uvicorn without `--reload`; no debug tracebacks returned to clients.
- [ ] Upload limits enforced server-side: type allow-list and `MAX_UPLOAD_MB` verified with real oversized and wrong-type files.
- [ ] Consistent JSON error format returned for every error path; no stack traces, file paths, SQL, or secrets in responses.
- [ ] 404 handler returns the standard error JSON for unknown routes and unknown document ids.
- [ ] 500 handler returns the standard `internal_error` JSON and logs the trace (never returns it).
- [ ] Empty states verified: empty document list and empty-corpus `/ask` return friendly responses.

## Security
- [ ] Filenames sanitized; confirmed a crafted filename (e.g. `../../etc/passwd`) cannot escape or be used as a path.
- [ ] Protected routes require `X-API-Key` when `API_KEY` is set; `GET /health` confirmed open.
- [ ] API key comparison is constant-time.
- [ ] Logs reviewed: no document contents, no question bodies beyond a short preview, no `ANTHROPIC_API_KEY` or `API_KEY`.
- [ ] Server bound to the intended interface (e.g. `127.0.0.1` for local-only; a fronting reverse proxy with TLS if exposed).

## Observability
- [ ] Structured JSON logging enabled at an appropriate `LOG_LEVEL`; each request has a request id echoed in `X-Request-ID`.
- [ ] Error tracking / alerting in place for `5xx` responses and upstream Claude API failures (log aggregation or an error tracker).
- [ ] A way to inspect `model_api_error`, `vector_store_error`, and `embedding_failed` rates.

## Data and persistence
- [ ] Verified data survives a process restart (documents still listed, `/ask` still works).
- [ ] SQLite migrations apply cleanly on a fresh `DATA_DIR` and are idempotent on an existing one.
- [ ] Backup/restore procedure for `DATA_DIR` (Chroma directory + SQLite file) documented and tested.
- [ ] Behavior of changing `EMBEDDING_MODEL` after indexing understood (requires re-index); documented for operators.

## Web UI (if built)
- [ ] Loading states present for upload and ask.
- [ ] Empty states present (no documents; empty answer).
- [ ] Error states present with `role="alert"` messaging.
- [ ] 404/500 responses render sensibly in the UI (not raw JSON dumps to the user).
- [ ] Mobile checked: usable at 375px width and at 200% zoom, no horizontal body scroll.
- [ ] Accessibility: labels, visible focus, keyboard operability, AA contrast in light and dark verified.
- [ ] No external CDN assets or web fonts; page works offline against the local API.

## Quality gates
- [ ] `uv run ruff check .` clean.
- [ ] `uv run black --check .` clean.
- [ ] `uv run pytest` passes with the Claude API mocked.
- [ ] `uv sync` produces a consistent environment from the committed `uv.lock`.
- [ ] README install/run/test steps followed on a clean machine and confirmed accurate.

## Project-specific
- [ ] Verified a full round trip on a fresh machine: upload -> list -> ask (cited answer) -> delete, for `.txt`, `.md`, and `.pdf`.
- [ ] Confirmed answers are grounded and citations point to real passages; a question with no supporting content yields a "not found" answer, not a fabrication.
- [ ] First-run local embedding model download completes (network available for that one-time fetch) and subsequent runs work offline for embedding.
- [ ] Cost expectations for the Claude API reviewed for the intended query volume and model (`CLAUDE_MODEL`).
