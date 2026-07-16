"""Chroma-backed vector store: add, query, and delete chunks.

Chroma is the source of truth for chunk text, embeddings, and chunk-level metadata. Access it
only through this module; routers and other services must not import chromadb directly.
"""

from pathlib import Path

import chromadb

from app.errors import VectorStoreError
from app.services.chunking import Chunk
from app.services.embeddings import build_embedding_function

COLLECTION_NAME = "askdocs_chunks"


class VectorStore:
    def __init__(self, data_dir: str, embedding_model: str = ""):
        chroma_dir = Path(data_dir) / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._client = chromadb.PersistentClient(path=str(chroma_dir))
            self._embedding_function = build_embedding_function(embedding_model)
            self._collection = self._client.get_or_create_collection(
                COLLECTION_NAME, embedding_function=self._embedding_function
            )
        except Exception as exc:
            raise VectorStoreError("Could not initialize the vector store.") from exc

    def add_chunks(self, document_id: str, filename: str, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        try:
            self._collection.add(
                ids=[f"{document_id}:{c.index}" for c in chunks],
                documents=[c.text for c in chunks],
                metadatas=[
                    {
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_index": c.index,
                        "char_start": c.char_start,
                        "char_end": c.char_end,
                    }
                    for c in chunks
                ],
            )
        except Exception as exc:
            raise VectorStoreError("Could not store document chunks.") from exc

    def query(self, question: str, top_k: int) -> list[dict]:
        try:
            result = self._collection.query(query_texts=[question], n_results=top_k)
        except Exception as exc:
            raise VectorStoreError("Could not query the vector store.") from exc

        documents = result.get("documents") or [[]]
        metadatas = result.get("metadatas") or [[]]
        distances = result.get("distances") or [[]]

        hits = []
        for doc_text, metadata, distance in zip(
            documents[0], metadatas[0], distances[0], strict=True
        ):
            score = max(0.0, 1.0 - distance / 2.0)
            hits.append(
                {
                    "document_id": metadata["document_id"],
                    "filename": metadata["filename"],
                    "chunk_index": metadata["chunk_index"],
                    "text": doc_text,
                    "score": round(score, 4),
                }
            )
        return hits

    def delete_document(self, document_id: str) -> None:
        try:
            self._collection.delete(where={"document_id": document_id})
        except Exception as exc:
            raise VectorStoreError("Could not delete document chunks.") from exc
