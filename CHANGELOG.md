# Changelog

## Unreleased

### Added
- CI runs lint, the format check, and tests on every push and pull request, with a 90 percent
  coverage gate.
- Tests for the Claude client wrapper and the CLI entry point.
- MIT license file.

### Fixed
- Citations list only the passages the answer used, instead of every retrieved passage.
- Uvicorn startup and access lines are emitted as JSON, and the duplicate access log is off.
- Upgraded pypdf, black, and transitive packages to resolve security advisories.

## 0.1.0

Upload `.txt`, `.md`, and `.pdf` documents, ask questions answered with citations from
local embeddings and Claude, list and delete documents, with optional API-key auth, a web UI,
and a CLI.
