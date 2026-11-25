"""Build the Chroma embedding function: local by default, overridable via EMBEDDING_MODEL.

Default: Chroma's bundled ONNX Runtime embedding function (all-MiniLM-L6-v2, 384-dim,
unit-normalized).
Override: a sentence-transformers model named by EMBEDDING_MODEL. The sentence-transformers
package is optional and not part of the default install; if EMBEDDING_MODEL is set but the
package is missing, this raises a clear EmbeddingFailedError rather than silently falling back.
"""

from chromadb.utils import embedding_functions

from app.errors import EmbeddingFailedError


def build_embedding_function(embedding_model: str):
    if not embedding_model:
        return embedding_functions.DefaultEmbeddingFunction()
    try:
        # Normalized vectors make Chroma's squared-L2 distance equal 2 - 2 * cosine, which is what
        # the vector store's score (1 - distance / 2) assumes. The bundled MiniLM is normalized.
        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model, normalize_embeddings=True
        )
    except Exception as exc:
        raise EmbeddingFailedError(
            f"Could not load embedding model {embedding_model!r}. "
            "Install the sentence-transformers extra or unset EMBEDDING_MODEL."
        ) from exc
