# askdocs

askdocs is a document question-answering service: you upload documents (`.txt`, `.md`, `.pdf`), askdocs extracts and chunks the text, embeds it into a persistent vector store, and then answers natural-language questions by retrieving the most relevant passages and asking Claude to compose an answer that cites the exact source chunks it used. It ships as a FastAPI application with a small optional single-page web UI and a CLI, and keeps all document text, metadata, and embeddings on local disk so it runs entirely on your own machine.

## Features

- Upload `.txt`, `.md`, and `.pdf` documents via a REST API (server-side validation of type and size).
- Automatic pipeline: extract text, chunk it, embed the chunks, and persist them.
- Ask natural-language questions and receive answers grounded in your documents, with citations back to the exact source passages.
- List and delete indexed documents.
- Persistent storage on disk (Chroma vector store plus a small SQLite metadata store) that survives restarts.
- Optional API-key authentication for all data routes.
- Optional minimal web UI (upload form, question box, answer with citation chips).
- Small CLI for add / list / delete / ask against a running server.
- Structured JSON logging and a single consistent JSON error format.

## Tech stack

- Python 3.11+
- FastAPI + Uvicorn (ASGI server)
- Pydantic v2 / pydantic-settings (models and configuration)
- ChromaDB (persistent vector store) with a local embedding model (sentence-transformers `all-MiniLM-L6-v2` via Chroma's default embedding function)
- SQLite (document metadata) via the standard-library `sqlite3` module
- `pypdf` (PDF text extraction)
- Anthropic Claude API (`anthropic` SDK) for answer composition
- pytest, Ruff, Black (tests, lint, format)

## Prerequisites

- Python 3.11 or newer
- An Anthropic API key (`ANTHROPIC_API_KEY`)
- `uv` (recommended) for dependency management and running the lockfile. Install from https://docs.astral.sh/uv/ .

## Install

```bash
git clone <your-fork-url> askdocs
cd askdocs
cp .env.example .env        # then edit .env and set ANTHROPIC_API_KEY
uv sync                     # creates .venv from pyproject.toml + uv.lock
```

## Run

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API base URL: `http://127.0.0.1:8000`
- Interactive docs (Swagger): `http://127.0.0.1:8000/docs`
- Web UI (if built): `http://127.0.0.1:8000/`

Quick smoke test:

```bash
curl -F "file=@README.md" http://127.0.0.1:8000/documents
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is askdocs?"}'
```

## Test

```bash
uv run ruff check .
uv run black --check .
uv run pytest
```

The Claude API is mocked in tests, so no network access or API key is required to run the suite.

## Structure

```
app/        FastAPI application: routers, services, schemas, config, errors, migrations
web/        Optional static single-page UI (index.html, app.js, styles.css)
cli/        Small CLI client (talks to the running API over HTTP)
tests/      pytest unit and integration tests
docs/       Planning and handoff documentation (PRD, architecture, rules, phases, ...)
```

See `docs/architecture.md` for the full file tree and data model.

License: MIT
