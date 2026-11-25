# Design decisions

## 1. Two stores linked by document id

Chroma holds chunk text, embeddings, and chunk metadata (`document_id`, `filename`,
`chunk_index`, `char_start`, `char_end`) in one collection, `askdocs_chunks`. SQLite holds one row
per document (filename, content type, size, chunk count, status, created time). Chroma is a poor
source of truth for listing documents, and SQLite cannot do similarity search, so each store owns
the data it is good at. Chunk ids are `{document_id}:{index}`, so a citation points at a stable
record, and deleting a document is one `where={"document_id": ...}` delete in Chroma plus one row
in SQLite.

## 2. Local embeddings by default

The Anthropic API has no embeddings endpoint, and a second hosted provider would mean a second
API key and sending every document off the machine. The default is Chroma's bundled
`all-MiniLM-L6-v2` (384 dimensions, ONNX Runtime), downloaded once on first use. `EMBEDDING_MODEL`
switches to a sentence-transformers model; if that package is not installed the store raises
`embedding_failed` instead of silently falling back to the default, because vectors from two
models are not comparable. For the same reason, changing `EMBEDDING_MODEL` after indexing
requires re-uploading the documents.

## 3. Fixed-size character chunks with overlap

Text is split into 1000-character windows that advance by 850, so neighbouring chunks share 150
characters and a sentence cut at a boundary still appears whole in one of them. Windows that are
only whitespace are skipped. Character windows need no tokenizer and behave the same for txt, md,
and PDF text. Each chunk keeps its `char_start` and `char_end`, so a citation can be traced back
to an exact span of the extracted text.

## 4. The model reports which passages it used

Retrieved passages are numbered `[1]..[k]` in the prompt, and the system prompt asks Claude to
answer only from them and to end with `SOURCES: 1, 3` or `SOURCES: none`. The line is stripped
from the answer and citations are filtered to the listed passages. Each passage is wrapped in a
`<passage number="n" source="...">` block and the question in a `<question>` block, closing tags
inside document text or the question are escaped so they cannot end a block early, and the system
prompt tells Claude that tagged text is untrusted data whose instructions it must not follow. Before this, every retrieved
passage was returned as a citation, so a question about receipts cited an unrelated PDF that
happened to rank in the top k. Numbers outside `1..k` are ignored. If the line is missing, or
names no valid passage, all retrieved passages are kept, so a reply that ignores the format still
shows where its answer could have come from.

## 5. An empty corpus is an answer, not an error

When no document is indexed, `POST /ask` returns `200` with a fixed message and no citations,
without calling Claude. Asking before uploading is a normal first step, not a client mistake, and
it should not cost a model call.

## 6. Ingestion is synchronous and keeps only text

An upload is extracted, chunked, embedded, and stored inside the request, and `201` means the
document is searchable. There is no job queue to run or poll. The file type comes from the
extension of the sanitized filename (directory parts and unsafe characters removed, so the client's
name is never a path), not from the client's declared content type. The handler reads the file up
to `MAX_UPLOAD_MB` plus one byte and rejects anything larger before extraction. The multipart parser
has already received the whole request body by then, so a deployment exposed beyond localhost
should also cap the request size in its reverse proxy.
Extraction and empty-text failures are raised before anything is written. The raw bytes are
discarded; only the extracted text survives, as chunks.

## 7. One error shape with stable codes

Every non-2xx response is `{"error": {"code", "message"}}`. Application errors carry their own
code and status, FastAPI validation errors become `validation_error`, Anthropic SDK errors become
`502 model_api_error`, and any unhandled exception becomes `500 internal_error`. Messages are safe
to show a user; stack traces, paths, and SDK details go to the log only. Clients, including the
CLI, can branch on `code` and print `message` without parsing anything else.

## 8. Optional API key on data routes

With `API_KEY` unset, everything is open, which suits a service bound to `127.0.0.1`. With it set,
the documents and ask routers require a matching `X-API-Key` header. The check is a router-level
dependency, so a new route on those routers cannot forget it, and it uses
`hmac.compare_digest` to avoid timing leaks. `GET /health` and the static web UI stay open.

## 9. Forward-only SQL migrations

The SQLite schema lives in numbered files in `app/migrations/`. On startup the metadata store
applies every file whose version is not yet in `schema_migrations`, in order, and records its
version. Committed migration files are never edited; a schema change is a new, higher-numbered
file. This keeps an existing `DATA_DIR` upgradable without an ORM or a migration tool.

## 10. One locked SQLite connection and per-directory store singletons

askdocs is a single local process, so the metadata store shares one connection across requests
(`check_same_thread=False`) behind a lock, rather than opening one per request. The metadata and
vector stores are cached in a dict keyed by `DATA_DIR` (and the embedding model for the vector
store) instead of `functools.lru_cache`, so tests that override `get_settings` with a temporary
directory get their own stores.

## 11. JSON logs with a request id

Every log line is one JSON object. A middleware assigns or reuses `X-Request-ID`, echoes it in the
response, and logs one `request_handled` line with route, status, and duration. Uvicorn's own
loggers go through the same JSON handler, and its access log is disabled because it duplicates
`request_handled`. Document text and secrets are never passed as log fields. The upload log uses
`document_filename` because `filename` is a reserved `LogRecord` attribute and raises on every
upload.

## 12. Deliberately out of scope

Plain top-k vector retrieval, one non-streaming `messages.create` call per question (1024 max
tokens), and no conversation history. No re-ranking, hybrid keyword search, query rewriting,
OCR for scanned PDFs, or formats beyond txt, md, and PDF. Each of these adds a dependency or a
moving part, and none is needed to answer questions over a personal document set with
verifiable citations.
