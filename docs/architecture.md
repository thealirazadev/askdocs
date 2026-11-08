# askdocs - Architecture

## Overview

askdocs is a single FastAPI process. HTTP requests hit thin routers that delegate to services. Services own the pipeline stages and the two on-disk stores (a Chroma vector store and a SQLite metadata database). Answer composition calls the Anthropic Claude API. The optional web UI and CLI are clients of the same HTTP API.

## Pipeline

```
                     POST /documents (multipart)
                              |
   upload  ->  validate (type + size, server-side)
           ->  sanitize filename, assign document id (uuid4 hex)
           ->  extract text        (services/extraction.py: txt/md/pdf)
           ->  chunk text          (services/chunking.py: fixed-size + overlap)
           ->  embed chunks        (services/embeddings.py: local model via Chroma)
           ->  store               (services/vectorstore.py -> Chroma collection)
           ->  record metadata     (services/metadata.py  -> SQLite documents row)
                              |
                     status = "indexed"

                          POST /ask {question}
                              |
   ask     ->  embed question (implicitly, via Chroma query)
           ->  retrieve top-k chunks   (services/vectorstore.py: query)
           ->  compose answer + citations (services/answering.py -> Claude API)
                              |
                 200 {answer, citations[]}
```

The pipeline is synchronous within a request. Ingestion for a single reasonably sized document completes inside one HTTP request; there is no background worker or job queue in scope (see Non-goals in `docs/PRD.md`).

## Proposed folder / file tree

```
askdocs/
├── app/
│   ├── __init__.py
│   ├── main.py                 # create FastAPI app, register routers + exception handlers, mount web/
│   ├── config.py               # Settings (pydantic-settings): env vars, defaults
│   ├── logging.py              # structured JSON logging setup; request id middleware helper
│   ├── errors.py               # AppError hierarchy + FastAPI exception handlers + error JSON shape
│   ├── deps.py                 # dependencies: get_settings, require_api_key, service singletons
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── health.py           # GET /health
│   │   ├── documents.py        # POST /documents, GET /documents, DELETE /documents/{id}
│   │   └── ask.py              # POST /ask
│   ├── services/
│   │   ├── __init__.py
│   │   ├── extraction.py       # extract_text(path|bytes, content_type) -> str
│   │   ├── chunking.py         # chunk_text(text) -> list[Chunk]
│   │   ├── embeddings.py       # build_embedding_function(settings) -> Chroma EF
│   │   ├── vectorstore.py      # VectorStore: add_chunks, query, delete_document
│   │   ├── metadata.py         # MetadataStore: SQLite access + migration runner
│   │   ├── claude_client.py    # thin wrapper around anthropic.Anthropic
│   │   └── answering.py        # answer_question(question, top_k) -> AnswerResult
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── documents.py        # DocumentOut, DocumentListOut, UploadResult
│   │   ├── ask.py              # AskRequest, AskResponse, Citation
│   │   └── errors.py           # ErrorBody, ErrorResponse
│   └── migrations/
│       └── 001_init.sql        # initial SQLite schema
├── web/                        # optional; Phase 4
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── cli/                        # optional; Phase 5
│   ├── __init__.py
│   └── askdocs_cli.py          # add / list / delete / ask over HTTP
├── tests/
│   ├── conftest.py             # fixtures: temp DATA_DIR, test client, mocked Claude client
│   ├── test_extraction.py
│   ├── test_chunking.py
│   ├── test_documents_api.py
│   ├── test_ask_api.py
│   └── test_auth.py
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
└── README.md
```

## Tech stack with rationale

- **FastAPI + Uvicorn** - typed request/response models, automatic OpenAPI docs, dependency injection for auth and settings, and a lightweight ASGI server. Fits a small, well-typed HTTP service.
- **Pydantic v2 + pydantic-settings** - request/response validation and environment-driven config in one consistent typing system. Config is read once at startup.
- **ChromaDB (PersistentClient)** - an embedded, on-disk vector database that ships with a built-in local embedding function, so the whole retrieval path runs locally with no extra service to operate. Handles embedding, storage, and similarity search of chunks together.
- **Local embedding model (`all-MiniLM-L6-v2` via Chroma's default embedding function)** - the Anthropic API does not provide an embeddings endpoint, so embeddings are produced locally. The Chroma default embedding function downloads and runs `all-MiniLM-L6-v2` through ONNX Runtime, keeping the default install to one required external dependency (the Claude API) and no second API key. See "Embedding approach" below.
- **SQLite via stdlib `sqlite3`** - durable document-level metadata (filename, size, status, counts, timestamps) with zero extra dependencies. Chroma is not a good source of truth for document-level listing/status, so metadata lives here.
- **`pypdf`** - pure-Python PDF text extraction, no system libraries required.
- **Anthropic Claude API (`anthropic` SDK)** - composes the final answer from retrieved chunks and produces citations. Model id: `claude-opus-5-5` (configurable via `CLAUDE_MODEL`; `claude-sonnet-5-5` or `claude-haiku-5-5` are lower-cost alternatives). Uses a single non-streaming `messages.create` call per question.
- **pytest / Ruff / Black** - tests, lint, format.

## Data model

Two stores. SQLite is the source of truth for documents; Chroma is the source of truth for chunks and embeddings. They are linked by `document_id`.

### SQLite: `documents` (metadata store)

| column        | type    | notes                                                             |
|---------------|---------|-------------------------------------------------------------------|
| id            | TEXT PK | uuid4 hex, generated on upload                                    |
| filename      | TEXT    | sanitized original filename                                       |
| content_type  | TEXT    | one of `text/plain`, `text/markdown`, `application/pdf`           |
| size_bytes    | INTEGER | raw uploaded byte length                                          |
| num_chunks    | INTEGER | number of chunks produced (0 until indexed)                       |
| status        | TEXT    | `indexed` or `failed`                                             |
| error         | TEXT    | nullable; failure reason when `status = failed`                   |
| created_at    | TEXT    | ISO-8601 UTC timestamp                                            |

A `schema_migrations` table (`version INTEGER PRIMARY KEY, applied_at TEXT`) tracks applied migrations.

### Chroma: collection `askdocs_chunks` (vector store + chunk metadata)

One record per chunk:

- **id**: `f"{document_id}:{chunk_index}"`
- **document** (text): the chunk text
- **embedding**: produced by the configured embedding function (default 384-dim `all-MiniLM-L6-v2`, cosine distance)
- **metadata** (embedding metadata): `document_id`, `filename`, `chunk_index` (int), `char_start` (int), `char_end` (int)

The `Chunk` value object used inside services carries: `index`, `text`, `char_start`, `char_end`.

A **citation** returned by `/ask` is assembled from a retrieved chunk: `document_id`, `filename`, `chunk_index`, `snippet` (a short excerpt of the chunk text), and `score` (similarity/relevance derived from Chroma distance).

## Where state lives

All persistent state is under `DATA_DIR` (default `./data`):

```
${DATA_DIR}/
├── chroma/            # Chroma PersistentClient directory (vectors + chunk metadata)
└── askdocs.db         # SQLite metadata database
```

Nothing is stored outside `DATA_DIR` except transient in-request buffers. `DATA_DIR` is created at startup if missing. No original upload bytes are persisted beyond the extracted text stored as chunks (the raw file is discarded after extraction).

### Embedding approach

- Default: local embeddings. The vector store uses Chroma's default embedding function (`all-MiniLM-L6-v2`, ONNX Runtime, 384 dimensions, cosine distance). No embedding API key is required and no document text leaves the machine for embedding.
- Override: `EMBEDDING_MODEL` may name a different `sentence-transformers` model; when set, the embeddings service constructs a sentence-transformers embedding function for that model (requires the optional `sentence-transformers` dependency).
- Using a hosted embeddings provider (for example Voyage AI, Anthropic's recommended embeddings partner) is explicitly out of scope for the default build; it is recorded in the backlog, not implemented. Anthropic's own API has no embeddings endpoint, so embeddings are never obtained from the Claude API.
- The embedding function is chosen once at startup. Changing `EMBEDDING_MODEL` after documents are indexed makes existing vectors incomparable to new queries; treat it as requiring a re-index (documented in `docs/rules.md`).

## External dependencies and required environment variables

External dependencies:
- Anthropic Claude API (network, requires `ANTHROPIC_API_KEY`) - answer composition.
- Local embedding model download - the Chroma default embedding function downloads `all-MiniLM-L6-v2` on first use and caches it; first run needs network access for that one-time download.

Environment variables (see `.env.example`):

| variable            | required | default          | purpose                                                                 |
|---------------------|----------|------------------|-------------------------------------------------------------------------|
| `ANTHROPIC_API_KEY` | yes      | -                | Authenticates calls to the Claude API.                                  |
| `DATA_DIR`          | no       | `./data`         | Root directory for the Chroma store and SQLite database.                |
| `CLAUDE_MODEL`      | no       | `claude-opus-5-5`| Claude model id used for answer composition.                            |
| `EMBEDDING_MODEL`   | no       | (Chroma default) | Optional sentence-transformers model id to override local embeddings.   |
| `API_KEY`           | no       | (unset)          | If set, data routes require this value in the `X-API-Key` header.        |
| `MAX_UPLOAD_MB`     | no       | `10`             | Maximum accepted upload size in megabytes (server-side enforced).       |
| `TOP_K`             | no       | `5`              | Number of chunks retrieved per question.                                |
| `LOG_LEVEL`         | no       | `INFO`           | Logging level for the structured logger.                                |

The Claude call uses `CLAUDE_MODEL`, `max_tokens` of `1024`, a system prompt instructing grounded, citation-only answers, and a single non-streaming `messages.create` request. No thinking configuration is required for this task.
