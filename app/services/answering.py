"""Compose a grounded, cited answer from retrieved chunks using Claude."""

from dataclasses import dataclass

from app.services.claude_client import ClaudeClient
from app.services.metadata import MetadataStore
from app.services.vectorstore import VectorStore

EMPTY_CORPUS_ANSWER = (
    "No documents have been indexed yet. Upload a document before asking a question."
)

SNIPPET_LENGTH = 240

SYSTEM_PROMPT = (
    "You are askdocs, a grounded question-answering assistant. Answer the user's question using "
    "only the numbered passages provided in the user message. If the passages do not contain the "
    "answer, say plainly that the documents do not contain the answer - do not fabricate "
    "information or cite passages you did not rely on. Respond with plain text only, no markdown "
    "headers, no passage numbers in the answer text itself."
)


@dataclass
class Citation:
    document_id: str
    filename: str
    chunk_index: int
    snippet: str
    score: float


@dataclass
class AnswerResult:
    answer: str
    citations: list[Citation]


def answer_question(
    question: str,
    top_k: int,
    vector_store: VectorStore,
    metadata_store: MetadataStore,
    claude_client: ClaudeClient,
) -> AnswerResult:
    if metadata_store.count_documents() == 0:
        return AnswerResult(answer=EMPTY_CORPUS_ANSWER, citations=[])

    hits = vector_store.query(question, top_k)
    if not hits:
        return AnswerResult(answer=EMPTY_CORPUS_ANSWER, citations=[])

    passages = "\n\n".join(
        f"[{i + 1}] (from {hit['filename']}, passage {hit['chunk_index']}): {hit['text']}"
        for i, hit in enumerate(hits)
    )
    user_message = f"Passages:\n{passages}\n\nQuestion: {question}"
    answer_text = claude_client.complete(SYSTEM_PROMPT, user_message)

    citations = [
        Citation(
            document_id=hit["document_id"],
            filename=hit["filename"],
            chunk_index=hit["chunk_index"],
            snippet=_snippet(hit["text"]),
            score=hit["score"],
        )
        for hit in hits
    ]
    return AnswerResult(answer=answer_text, citations=citations)


def _snippet(text: str) -> str:
    stripped = text.strip()
    if len(stripped) <= SNIPPET_LENGTH:
        return stripped
    return stripped[:SNIPPET_LENGTH].rsplit(" ", 1)[0] + "..."
