# askdocs - Rules and Conventions

These rules are binding for anyone (human or agent) implementing askdocs. They are specific to this project.

## Conventions

### Preferred libraries and patterns
- HTTP layer: FastAPI. One `APIRouter` per resource in `app/routers/`. Routers stay thin - parse/validate input, call a service, shape the response. No business logic in routers.
- Data validation and config: Pydantic v2 for request/response models (`app/schemas/`), pydantic-settings for configuration (`app/config.py`). Read settings once at startup via a cached `get_settings()` dependency.
- Services in `app/services/` own the pipeline stages and the stores. Services are plain classes/functions and do not import FastAPI.
- Vector store: ChromaDB `PersistentClient`. Access it only through `services/vectorstore.py`. Do not call Chroma from routers.
- Metadata store: standard-library `sqlite3` through `services/metadata.py`. Use parameterized queries only; never string-format SQL. Open connections with `check_same_thread=False` guarded by a lock, or a per-request connection - pick one and keep it consistent.
- Claude access: only through `services/claude_client.py`. Use the official `anthropic` SDK, a single non-streaming `messages.create` call for answering. Do not add a second LLM provider.
- Filesystem: everything persistent lives under `DATA_DIR`. Never write outside it.
- IDs: `uuid4().hex` for document ids. Chunk ids are `f"{document_id}:{index}"`.
- Timestamps: ISO-8601 UTC strings.

### What to avoid
- No ORM (SQLAlchemy, SQLModel, etc.). Plain `sqlite3` is sufficient and keeps the metadata layer small.
- No background task queue, Celery, Redis, or async workers. Ingestion is synchronous.
- No second LLM or embeddings provider in the default build. No hosted embeddings API.
- No global mutable state beyond the initialized store singletons created at startup.
- No `print()` for diagnostics - use the structured logger.
- No raw f-string SQL, no `eval`, no dynamic imports.
- Do not persist raw uploaded file bytes; keep only extracted text as chunks.

### Naming
- PEP 8. `snake_case` for functions/variables/modules, `PascalCase` for classes, `UPPER_SNAKE` for constants.
- Modules named for their role: `extraction.py`, `chunking.py`, `embeddings.py`, `vectorstore.py`, `metadata.py`, `answering.py`.
- Pydantic response models end in `Out` or `Response`; request models end in `Request`.
- Environment variables are `UPPER_SNAKE` and mirrored exactly by `Settings` fields (lowercased).

### Commit format
- Conventional Commits with a short, imperative subject: `type(scope): subject`.
- Allowed types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `build`.
- Scope is the area touched, e.g. `feat(documents): add upload endpoint`, `feat(ask): compose answer with citations`, `test(chunking): cover overlap boundaries`.
- Subject in the imperative mood, no trailing period, lower case, under ~70 characters.

### One commit per feature / task
- Each feature or task from `docs/phases.md` is exactly one commit. Do not batch multiple features into one commit, and do not split one feature across many noise commits. The "Commits" list in each phase is the intended commit sequence, in order.

### Dependencies and lockfile
- Pin exact dependency versions. Use `uv` with `pyproject.toml` and a committed `uv.lock`. Every dependency in `pyproject.toml` is pinned to an exact version (`==`), and `uv.lock` is committed alongside it.
- Adding, removing, or upgrading any dependency is its own `build:` commit and must include the updated `uv.lock`.
- Do not introduce a dependency that is not already approved in `docs/architecture.md` without explicit approval (see Boundaries).

### SQL metadata store - migration rule
- The metadata database is versioned by numbered SQL files in `app/migrations/` (`001_init.sql`, `002_*.sql`, ...).
- A `schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT)` table records applied migrations.
- On startup, `services/metadata.py` applies every migration whose version is greater than the current max recorded version, in ascending order, inside a transaction, then records it.
- Never edit an already-committed migration file. Schema changes are new, higher-numbered migration files. Migrations are forward-only (no down migrations in scope).

## Error handling and logging

### Failures to handle explicitly
- **File parsing / extraction**: unreadable or corrupt file, unsupported type, or a PDF with no extractable text -> reject the upload with a clear client error; do not create a half-indexed document. If a document was partially recorded, mark it `failed` with an `error` reason.
- **Embedding**: embedding model load or encode failure -> fail the ingestion request with a `502`/`503`-class error and log the cause; do not leave orphan chunks in Chroma without a metadata row.
- **Vector store**: Chroma add/query/delete failure -> surface a service-unavailable error to the client, log details.
- **Model API**: Anthropic errors (auth, rate limit, connection, 5xx) -> catch the SDK's typed exceptions, map to a friendly client error, and log the specifics (status, request id) without the document text.

### Friendly API errors vs detailed logs
- API responses contain a short, human-readable message and a stable machine `code`. They never contain stack traces, internal file paths, SQL, or SDK internals.
- Logs contain the full detail (exception type, stack trace where useful, upstream status codes, request ids) at the appropriate level.

### Never leak stack traces
- A catch-all exception handler converts any unhandled exception into the standard error JSON with `code: "internal_error"` and HTTP `500`. The stack trace goes to the log only.

### One consistent JSON error format
Every error response - validation, auth, not-found, upstream, internal - uses this shape:

```json
{
  "error": {
    "code": "unsupported_file_type",
    "message": "Only .txt, .md, and .pdf files are supported."
  }
}
```

- `code` is a stable snake_case string. Defined codes: `validation_error`, `unauthorized`, `not_found`, `unsupported_file_type`, `file_too_large`, `empty_document`, `no_documents_indexed`, `extraction_failed`, `embedding_failed`, `vector_store_error`, `model_api_error`, `internal_error`.
- Pydantic/FastAPI validation errors are translated into this shape (do not expose the default FastAPI `detail` array as-is).

### Structured logging from day one
- Use Python `logging` configured in `app/logging.py` to emit one JSON object per line: `timestamp`, `level`, `logger`, `message`, plus contextual fields (`request_id`, `route`, `document_id`, `status_code`, `duration_ms`, `error_code`).
- Assign a request id per request (middleware) and include it in every log line for that request and in the response headers (`X-Request-ID`).
- Log level from `LOG_LEVEL`.

## Security

- **Never hardcode secrets.** No API keys, tokens, or credentials in source, tests, or fixtures.
- **Config via `.env` + `.env.example`.** Real values live in `.env` (git-ignored). `.env.example` documents every variable with dummy values only.
- **Validate uploads server-side.** Enforce allowed file types (by extension and content type: `.txt`/`text/plain`, `.md`/`text/markdown`, `.pdf`/`application/pdf`) and a maximum size (`MAX_UPLOAD_MB`) on the server. Do not trust client-side checks. Read the body with the size limit enforced so an oversized upload is rejected before full buffering where feasible; reject with `413`.
- **Sanitize filenames.** Strip directory components and unsafe characters; never use a client-supplied filename as a filesystem path or in a shell command. Store the sanitized name for display only.
- **Optional API key auth.** When `API_KEY` is set, all data routes (`/documents` POST/GET/DELETE, `/ask`) require a matching `X-API-Key` header, enforced by a FastAPI dependency. When `API_KEY` is unset, those routes are open (local convenience). `GET /health` is always open. Compare keys with a constant-time comparison.
- **Do not log document contents or the API key.** Log document ids, filenames, sizes, and counts - never chunk text, question text bodies beyond a short truncated preview if needed, or any secret. Redact `ANTHROPIC_API_KEY` and `API_KEY` everywhere.
- **Document protected routes.** The OpenAPI schema and `docs/api-contracts.md` state which routes require `X-API-Key`. Protected: `POST /documents`, `GET /documents`, `DELETE /documents/{id}`, `POST /ask`. Open: `GET /health`, and static web assets.

## Simplicity / YAGNI / KISS

- Build only what a phase in `docs/phases.md` requires. Do not add abstractions, config options, or endpoints for hypothetical futures.
- Prefer the simplest thing that works: a fixed-size chunker, plain top-k retrieval, a single Claude call. No caching layers, no re-rankers, no plugin systems.
- Do not add error handling for conditions that cannot occur given the validated inputs; validate at the boundary (upload, request body) and trust internal invariants.
- One module, one job. If a service grows past its role, that is a signal to split, not to add flags.

## Code style

- Sparse comments: explain non-obvious decisions and invariants, not what the line does. No commented-out code.
- Concise docstrings: one line for simple functions; a short paragraph for services and non-obvious behavior. Document units and error behavior where relevant.
- No emoji anywhere in code, comments, docstrings, logs, or docs.
- No authorship attribution: never add "generated by", "co-authored by", or any claim that an assistant wrote the code, in source, comments, or commit messages.
- Format with Black, lint with Ruff; both must pass before a feature is considered done.
- Conventional Commits (see Conventions).

## Boundaries

- **No wholesale delete/rewrite.** Make focused, minimal changes. Do not rewrite files or modules that are not part of the current task.
- **Do not change PRD or architecture without flagging.** If a task seems to require deviating from `docs/PRD.md` or `docs/architecture.md`, stop and flag it explicitly with the reason and proposed change before proceeding.
- **No new dependency without approval.** Only the dependencies named in `docs/architecture.md` are pre-approved. Any other dependency requires explicit approval first.
- **Ask when ambiguous.** If requirements are unclear or two reasonable interpretations exist, ask rather than guess.
- **Stop after two failed fix attempts.** If two attempts to fix the same failure do not work, stop and report what was tried, the observed behavior, and a hypothesis - do not keep churning.
- **Scope changes explicitly.** Classify any newly discovered work as: (a) part of the current phase, (b) a new phase, or (c) backlog. Put it in the right place in `docs/phases.md` (or `docs/memory.md` for backlog) rather than silently expanding the current task.
