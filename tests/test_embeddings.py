import pytest

from app.errors import EmbeddingFailedError
from app.services import embeddings


def test_sentence_transformer_vectors_are_normalized(monkeypatch):
    calls = []

    def fake_function(**kwargs):
        calls.append(kwargs)
        return "embedding-function"

    monkeypatch.setattr(
        embeddings.embedding_functions, "SentenceTransformerEmbeddingFunction", fake_function
    )

    assert embeddings.build_embedding_function("all-mpnet-base-v2") == "embedding-function"
    assert calls == [{"model_name": "all-mpnet-base-v2", "normalize_embeddings": True}]


def test_a_model_that_cannot_load_raises_embedding_failed(monkeypatch):
    def broken(**kwargs):
        raise ValueError("sentence-transformers is not installed")

    monkeypatch.setattr(
        embeddings.embedding_functions, "SentenceTransformerEmbeddingFunction", broken
    )

    with pytest.raises(EmbeddingFailedError):
        embeddings.build_embedding_function("missing-model")
