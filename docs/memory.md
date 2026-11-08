# askdocs - Project Memory

Running log of what is done, what is in flight, and decisions made. Keep entries short and dated. Update this as work proceeds; it is the handoff state between work sessions.

## Completed

- 2026-07-15: Planning documentation created (README, PRD, architecture, rules, design, api-contracts, phases, testing, launch-checklist, .env.example).
- 2026-07-17: Phase 1 (core Q&A over text files) implemented and committed: config, structured
  logging + request-id middleware, error schema/handlers, FastAPI app + health route, SQLite
  metadata store with migration runner, txt/md extraction, fixed-size chunker, local Chroma
  embeddings, vector store wrapper, upload/list/delete document endpoints, Anthropic client
  wrapper, `/ask` with citations, and the phase-1 test suite (mocked Claude, real temp
  Chroma/SQLite). 22 tests passing at phase end.
- 2026-07-17: Phase 2 (PDF support) implemented and committed: `pypdf` dependency, PDF text
  extraction wired into the existing upload pipeline, hand-built PDF fixtures
  (`tests/fixtures/{sample,empty,corrupt}.pdf`) and tests for normal/empty/corrupt PDFs.
- 2026-07-17: Phase 3 (optional API-key auth) implemented and committed: `require_api_key`
  dependency in `app/deps.py` using `hmac.compare_digest`, applied at the router level to
  `documents` and `ask` routers (`GET /health` stays open); auth tests cover open/authorized/
  rejected paths.
- 2026-07-17: Phase 4 (minimal web UI) implemented and committed: static `web/index.html`,
  `web/styles.css`, `web/app.js` (upload/list/delete/ask, loading/empty/error states, citation
  chips with expandable snippet, API-key prompt + retry on 401, no external CDN/fonts); mounted
  under `/web` with `GET /` serving `index.html` from `app/main.py`.
- 2026-07-17: Phase 5 (CLI) implemented and committed: `cli/askdocs_cli.py` (`add`/`list`/
  `delete`/`ask` over HTTP via `httpx`, base URL/API key from flags or
  `ASKDOCS_URL`/`ASKDOCS_API_KEY`), with argument-parsing and mocked-transport request tests.
- 2026-07-17: Reconstructed and committed all of the above from previously uncommitted working-
  tree code (`app/`, `cli/`, `tests/`) into the phase-ordered commit sequence from
  `docs/phases.md`; nothing was rewritten wholesale, only split/reassembled into the intended
  commits. Full suite at HEAD: 44 tests passing, `ruff check .` and `black --check .` clean.

## In progress

- (none - all five phases in `docs/phases.md` are complete)

## Decisions log

- 2026-07-15: Vector store is ChromaDB `PersistentClient`; document-level metadata is a separate SQLite database. Chroma is source of truth for chunks/embeddings; SQLite is source of truth for document listing/status. Linked by `document_id`.
- 2026-07-15: Embeddings are local by default (Chroma default embedding function, `all-MiniLM-L6-v2`, 384-dim, cosine). The Anthropic API has no embeddings endpoint. `EMBEDDING_MODEL` overrides to a sentence-transformers model. Hosted embeddings (e.g. Voyage AI) are backlog, not in the default build.
- 2026-07-15: Answer composition uses a single non-streaming Anthropic `messages.create` call. Default model `claude-opus-4-8` (configurable via `CLAUDE_MODEL`; `claude-sonnet-5`/`claude-haiku-4-5` are lower-cost alternatives).
- 2026-07-15: Dependency management via `uv` with pinned versions in `pyproject.toml` and a committed `uv.lock`.
- 2026-07-15: SQLite schema is versioned via numbered files in `app/migrations/` with a `schema_migrations` table; migrations are forward-only and never edited after commit.
- 2026-07-15: Auth is optional, keyed on the `API_KEY` env var, enforced via `X-API-Key` on data routes only; `GET /health` always open.
- 2026-07-15: One consistent JSON error format `{ "error": { "code", "message" } }`; empty-corpus `/ask` is a friendly `200`, not an error.
- 2026-07-17: Pinned exact versions for the previously empty `pyproject.toml` dependency list
  (fastapi 0.115.6, uvicorn 0.34.0, pydantic 2.10.4, pydantic-settings 2.7.0, python-multipart
  0.0.20, chromadb 0.5.23, anthropic 0.42.0, pypdf 5.1.0, httpx 0.28.1; dev: pytest 8.3.4, ruff
  0.8.4, black 24.10.0) and generated `uv.lock`. `python-multipart` was added beyond the
  architecture doc's explicit list because FastAPI's `UploadFile` requires it for multipart
  form parsing - flagging here since it wasn't separately called out in `docs/architecture.md`.
  `httpx` started as a dev-only dependency (required by FastAPI's `TestClient`) and was promoted
  to a main dependency in the phase-5 `build: add httpx dependency for cli` commit once the CLI
  needed it at runtime.
- 2026-07-17: Added `ignore = ["B008"]` to `[tool.ruff.lint]`: ruff's flake8-bugbear rule flags
  `Depends(...)` as a "function call in a default argument", which is FastAPI's standard
  dependency-injection pattern, not a bug.
- 2026-07-17: Fixed a real bug found while getting the test suite green: `documents.py` logged
  `extra={"filename": filename, ...}` on upload, but `filename` collides with a reserved
  attribute of stdlib `logging.LogRecord`, so every successful upload raised
  `KeyError: "Attempt to overwrite 'filename' in LogRecord"` from inside the exception handler
  itself. Renamed the log field to `document_filename`.
- 2026-07-17: PDF test fixtures (`tests/fixtures/{sample,empty,corrupt}.pdf`) are hand-built
  minimal PDF byte streams (no external PDF-generation dependency available/approved) rather
  than generated by a library; `sample.pdf` contains extractable text, `empty.pdf` has a valid
  but empty content stream, `corrupt.pdf` is deliberately truncated.

## Real-model manual run (2026-11-09)

- Ran all phase 1 and phase 3 manual checks against Claude Opus 5.5 through a local
  Anthropic-Messages shim (it calls the Claude Code CLI and lived outside the repo), with the
  bundled MiniLM embeddings. A policy file answered "London hotel limit and when can I take a
  taxi" exactly (220 EUR; after 21:00 or with equipment over 10 kg) with a citation to the file
  and chunk 0; a question not covered ("Tokyo per diem") was answered as not specified, citing
  only the closest general rules. 415/413/422, empty-store 200, delete 204 then 404, restart
  persistence, text PDF upload and grounded answer, and empty PDF 400 all behaved as specified.
- Fixed: uvicorn's own startup and access lines were plain text in an otherwise JSON log
  stream. uvicorn loggers now go through the JSON handler, its access log (a duplicate of
  `request_handled`) is off, and its `color_message` ANSI copy is dropped.
- **Flagged architecture.md change:** default model `claude-opus-4-8` -> `claude-opus-5-5`
  (and the listed cheaper alternatives to the 5.5 generation). Only the model id changed; the
  rule that it lives in config is unchanged.
- Also verified: corrupt PDF 422, API_KEY on/off/wrong/right with `/health` open and the key
  absent from logs, CLI add/list/ask with `ASKDOCS_API_KEY` and `--api-key` (and exit 1
  without a key). CLI delete and down-server (friendly error, exit 1) also pass. Not yet run: the web UI checks.
- Fixed: citations were every retrieved passage, so "how many days to submit receipts" cited
  an unrelated PDF. The model now ends with `SOURCES: n, m` (or `none`); citations are
  filtered to those, and a missing or out-of-range line keeps all passages as before.
