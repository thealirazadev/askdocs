# askdocs - Product Requirements

## What we are building

askdocs is a local-first document question-answering service. A user uploads a set of documents, askdocs indexes them into a persistent vector store, and the user can then ask natural-language questions and receive answers that are grounded in those documents. Every answer is accompanied by citations that point back to the specific source passages used, so the user can verify the answer against the original text.

The product is delivered as a FastAPI HTTP service. A minimal single-page web UI and a small CLI are thin clients over that API.

## Target user

A developer or technically comfortable individual who has a modest collection of documents (notes, specs, manuals, PDFs) and wants to ask questions across them without sending the documents to a hosted third-party product. They run askdocs on their own machine, provide their own Anthropic API key, and keep all document data on local disk. They value: grounded answers, verifiable citations, simple setup, and data staying local.

This is not a multi-tenant SaaS. There is a single implicit user / workspace per running instance.

## Core features (prioritized)

1. **Upload and index documents** (highest priority). Accept `.txt`, `.md`, and `.pdf` uploads over HTTP, extract their text, chunk it, embed the chunks, and persist them. Without this nothing else works.
2. **Ask questions with cited answers** (highest priority). Given a question, retrieve the top-k most relevant chunks and use the Claude API to compose an answer that cites the chunks it relied on.
3. **List indexed documents.** Show what has been indexed (id, filename, size, chunk count, status, created time).
4. **Delete a document.** Remove a document and all of its chunks/embeddings from the store.
5. **Persistence across restarts.** All indexed data (vectors and metadata) lives on disk and is available after the process restarts.
6. **Optional API-key authentication.** When an API key is configured, all data routes require it.
7. **Minimal web UI** (lower priority). One page: upload, ask, and view the answer with citation chips.
8. **CLI** (lower priority). `add`, `list`, `delete`, `ask` against a running server.

## Non-goals

- Multi-user accounts, roles, sharing, or per-user isolation.
- Hosted/cloud deployment, horizontal scaling, or a managed database. Disk-backed local storage only.
- OCR of scanned/image-only PDFs. Only extractable text is supported; a PDF with no extractable text is reported as such.
- Document formats beyond `.txt`, `.md`, `.pdf` (no `.docx`, `.html`, `.csv`, etc.).
- Re-ranking models, hybrid keyword+vector search, or query rewriting. Plain top-k vector retrieval only.
- Streaming answers, chat history / multi-turn conversation memory, or follow-up context.
- Automatic re-indexing on file change or folder watching.
- Fine-tuning or training. askdocs only calls the Claude API for inference.

## Success criteria per core feature

**1. Upload and index documents**
- Uploading a supported file returns `201` with a document id, filename, and chunk count.
- The extracted text is chunked and every chunk is embedded and stored; the document status becomes `indexed`.
- Unsupported file types are rejected with `415` and the consistent error format; oversized files are rejected with `413`.
- Filenames are sanitized before use; the original raw filename is never used as a filesystem path.

**2. Ask questions with cited answers**
- A question against an indexed corpus returns `200` with a non-empty `answer` and a `citations` array.
- Each citation references a real indexed document (by id and filename) and a real passage (chunk index plus a text snippet).
- When no documents are indexed, `/ask` returns a clear, friendly response indicating there is nothing to search (not a stack trace).
- When retrieved context does not contain the answer, the answer says so rather than fabricating; it does not cite passages it did not use.

**3. List indexed documents**
- `GET /documents` returns all indexed documents with id, filename, size, chunk count, status, and created timestamp.
- The list reflects deletions immediately.

**4. Delete a document**
- `DELETE /documents/{id}` removes the document's metadata and all of its chunks/embeddings, returns `204`, and the document no longer appears in the list or in future answers.
- Deleting an unknown id returns `404` in the consistent error format.

**5. Persistence across restarts**
- After indexing documents and restarting the process, `GET /documents` and `/ask` return the same indexed data with no re-upload.

**6. Optional API-key authentication**
- With `API_KEY` unset, all routes work without a key (local convenience).
- With `API_KEY` set, data routes require a matching `X-API-Key` header; a missing or wrong key returns `401`. `GET /health` is always open.

**7. Minimal web UI**
- The page lets a user upload a file, type a question, and see the answer with citation chips. Loading, empty, and error states are visible and accessible.

**8. CLI**
- `add`, `list`, `delete`, and `ask` each work against a running server and print readable output, including citations for `ask`.
