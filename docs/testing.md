# askdocs - Testing

## Strategy

- **pytest** is the test framework. The Claude API is always mocked: no test makes a real network call to Anthropic and no test requires `ANTHROPIC_API_KEY`.
- **Unit tests** cover the pure pipeline stages (extraction, chunking, the Claude client wrapper, logging setup, CLI argument handling). **Integration tests** exercise the HTTP endpoints end to end through FastAPI's `TestClient` with a temporary `DATA_DIR`, a real (temporary) Chroma store and SQLite database, and a mocked Claude client.
- Browser UI behavior and answer quality against a real model are checked by hand, not automated.

### What is mocked vs real
- **Mocked**: the Anthropic client (`services/claude_client.py`), replaced through a fixture and a dependency override so `/ask` gets a deterministic reply. Tests assert on retrieval and citation building, not on model text. Citation filtering is tested by having the mock reply with a `SOURCES:` line that names specific passages, `none`, or an out-of-range number.
- **Real (but temporary)**: Chroma and SQLite run for real against a per-test temp `DATA_DIR`, so persistence, deletion, and migrations are genuinely exercised. The local embedding model runs for real; test documents are kept tiny so it stays fast.

### Test layout
- `tests/conftest.py`: fixtures `tmp_data_dir` (temp `DATA_DIR`), `client` (FastAPI `TestClient` with settings pointing at the temp dir), `mock_claude` (mocked Claude client), and a helper to upload a small in-memory document.
- `tests/test_extraction.py`: txt/md extraction, PDF extraction, empty-text and corrupt-file behavior.
- `tests/test_chunking.py`: chunk sizes, overlap boundaries, short input (single chunk), and that `char_start`/`char_end` are correct and contiguous with overlap.
- `tests/test_documents_api.py`: upload success, unsupported type (`415`), oversized (`413`), empty document (`400`), PDF upload, empty and corrupt PDFs, list, delete (`204`), delete unknown (`404`), and persistence across a fresh store pointed at the same dir.
- `tests/test_ask_api.py`: answer plus citations referencing real chunks, empty question (`422`), over-long question (`422`), empty-corpus friendly `200`, model API error mapping (`502`), and citation filtering by the `SOURCES:` line.
- `tests/test_answering.py`: passages and the question fenced in tags, closing tags inside them escaped, and the untrusted-content instruction in the system prompt.
- `tests/test_embeddings.py`: a sentence-transformers model is loaded with normalized vectors, and a model that cannot load raises `embedding_failed`.
- `tests/test_auth.py`: open when `API_KEY` is unset, allowed with the correct key, `401` with a missing or wrong key, health open regardless.
- `tests/test_claude_client.py`: the Anthropic wrapper's request shape and error mapping.
- `tests/test_cli.py`, `tests/test_cli_main.py`: argument parsing, request building against a mocked HTTP layer, the API key header, and friendly exits on errors.
- `tests/test_logging_setup.py`: uvicorn logs routed through the JSON handler, with its ANSI colour copy dropped.

Coverage of `app` and `cli` is measured on every run, and CI fails below 90 percent (`[tool.coverage.report] fail_under` in `pyproject.toml`).

## Exact commands

Run from the project root with `uv`.

Install / sync dependencies:
```bash
uv sync
```

Lint:
```bash
uv run ruff check .
```

Format check (and auto-format):
```bash
uv run black --check .
uv run black .            # to apply formatting
```

Tests:
```bash
uv run pytest
uv run pytest -q                       # quiet
uv run pytest tests/test_ask_api.py    # a single file
```

Import check (this is a Python app; a clean sync plus a successful app import stands in for a build):
```bash
uv sync
uv run python -c "import app.main"
```

## Before merging

From a clean checkout, all of these must succeed (CI runs the sync, lint, format check, and tests on every push and pull request):

```bash
uv sync
uv run ruff check .
uv run black --check .
uv run python -c "import app.main"
uv run pytest
```
