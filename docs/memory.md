# askdocs - Project Memory

Running log of what is done, what is in flight, and decisions made. Keep entries short and dated. Update this as work proceeds; it is the handoff state between work sessions.

## Completed

- 2026-07-15: Planning documentation created (README, PRD, architecture, rules, design, api-contracts, phases, testing, launch-checklist, .env.example).

## In progress

- (none yet)

## Decisions log

- 2026-07-15: Vector store is ChromaDB `PersistentClient`; document-level metadata is a separate SQLite database. Chroma is source of truth for chunks/embeddings; SQLite is source of truth for document listing/status. Linked by `document_id`.
- 2026-07-15: Embeddings are local by default (Chroma default embedding function, `all-MiniLM-L6-v2`, 384-dim, cosine). The Anthropic API has no embeddings endpoint. `EMBEDDING_MODEL` overrides to a sentence-transformers model. Hosted embeddings (e.g. Voyage AI) are backlog, not in the default build.
- 2026-07-15: Answer composition uses a single non-streaming Anthropic `messages.create` call. Default model `claude-opus-4-8` (configurable via `CLAUDE_MODEL`; `claude-sonnet-5`/`claude-haiku-4-5` are lower-cost alternatives).
- 2026-07-15: Dependency management via `uv` with pinned versions in `pyproject.toml` and a committed `uv.lock`.
- 2026-07-15: SQLite schema is versioned via numbered files in `app/migrations/` with a `schema_migrations` table; migrations are forward-only and never edited after commit.
- 2026-07-15: Auth is optional, keyed on the `API_KEY` env var, enforced via `X-API-Key` on data routes only; `GET /health` always open.
- 2026-07-15: One consistent JSON error format `{ "error": { "code", "message" } }`; empty-corpus `/ask` is a friendly `200`, not an error.
