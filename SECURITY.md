# Security policy

## Supported versions

Only the latest release (0.1.0, the version in `pyproject.toml`) on `main` receives security
fixes.

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's private vulnerability reporting
(Security tab, "Report a vulnerability") or email thealirazadev@gmail.com with the
steps to reproduce. You should get a reply within 72 hours.

## How askdocs protects documents and keys

- The optional `X-API-Key` check on data routes uses a constant-time comparison, and the key
  and header value are never logged.
- Uploads are limited to `.txt`, `.md`, and `.pdf` files, and the size limit (10 MB by default,
  `MAX_UPLOAD_MB`) is enforced while the file is read, so oversized bodies are rejected early.
- Questions are capped at 2000 characters and validated before any model call.
- Document text, metadata, and embeddings stay on local disk. Only the passages retrieved for a
  question are sent to the Claude API.
- Log lines are structured JSON, and secrets such as `ANTHROPIC_API_KEY` and `API_KEY` are not
  passed as log fields.
