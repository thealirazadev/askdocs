# askdocs - Testing

## Strategy

- **pytest** is the test framework. The Claude API is always mocked - no test makes a real network call to Anthropic and no test requires `ANTHROPIC_API_KEY`.
- Favor **unit tests** for the pure pipeline stages (extraction, chunking, error mapping) plus a **couple of integration tests** that exercise the HTTP endpoints end-to-end through FastAPI's `TestClient` with a temporary `DATA_DIR`, a real (temporary) Chroma store and SQLite database, and a mocked Claude client.
- Everything else (browser UI behavior, exact answer quality) is covered by the manual QA checklists in `docs/phases.md`, not automated.

### What is mocked vs real
- **Mocked**: the Anthropic client (`services/claude_client.py`). Patch it (via a fixture and dependency override) so `answer_question` returns a deterministic answer built from the retrieved chunks. Assert on the retrieval and citation-building behavior, not on model text.
- **Real (but temporary)**: Chroma and SQLite run for real against a per-test temp `DATA_DIR`, so persistence, deletion, and migrations are genuinely exercised. The local embedding model runs for real; keep test documents tiny to keep it fast. If the embedding model download is a problem in CI, allow a fixture to substitute a small deterministic embedding function - but the default is the real local one.

### Test layout and coverage targets
- `tests/conftest.py` - fixtures: `tmp_data_dir` (temp `DATA_DIR`), `client` (FastAPI `TestClient` with settings pointing at the temp dir), `mock_claude` (patched Claude client), and a helper to upload a small in-memory document.
- `tests/test_extraction.py` - txt/md extraction, PDF extraction (Phase 2), empty-text and corrupt-file behavior.
- `tests/test_chunking.py` - chunk sizes, overlap boundaries, short input (single chunk), and that `char_start`/`char_end` are correct and contiguous with overlap.
- `tests/test_documents_api.py` - upload success, unsupported type (`415`), oversized (`413`), empty document (`400`), list, delete (`204`), delete unknown (`404`), and persistence across a fresh store pointed at the same dir.
- `tests/test_ask_api.py` - ask returns answer + citations referencing real chunks, empty-question (`422`), over-long question (`422`), empty-corpus friendly `200`, and model-API-error mapping (`502`) by making the mocked client raise.
- `tests/test_auth.py` (Phase 3) - open when `API_KEY` unset, allowed with correct key, `401` with missing/wrong key, health open regardless.
- `tests/` CLI tests (Phase 5) - argument parsing and request building against a mocked HTTP layer.

Aim for meaningful coverage of every service and every documented error path, not a coverage percentage. Every error `code` in `docs/api-contracts.md` should be produced by at least one test.

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

"Build" (this is a Python app; the build gate is a clean sync plus a successful app import):
```bash
uv sync
uv run python -c "import app.main"
```

## Definition of done for any feature

A feature (one commit per `docs/phases.md`) is not done until, from a clean checkout:

```bash
uv sync
uv run ruff check .
uv run black --check .
uv run python -c "import app.main"
uv run pytest
```

all succeed. Build and tests must pass before a feature is considered complete and committed. If any of these fail, the feature is not done - fix it or, after two failed attempts on the same failure, stop and report (see Boundaries in `docs/rules.md`).
