"""Shared FastAPI dependencies: settings and service singletons.

Store instances are cached by data_dir (and, for the vector store, embedding_model) rather than
via functools.lru_cache on a zero-arg call, so that the FastAPI dependency-override mechanism
used in tests (overriding get_settings) is honored - each distinct data_dir gets its own
singleton. This is the "initialized store singleton" global state permitted by docs/rules.md.
"""

from fastapi import Depends

from app.config import Settings, get_settings
from app.services.metadata import MetadataStore
from app.services.vectorstore import VectorStore

_metadata_stores: dict[str, MetadataStore] = {}
_vector_stores: dict[tuple[str, str], VectorStore] = {}


def get_metadata_store(settings: Settings = Depends(get_settings)) -> MetadataStore:
    store = _metadata_stores.get(settings.data_dir)
    if store is None:
        store = MetadataStore(settings.data_dir)
        _metadata_stores[settings.data_dir] = store
    return store


def get_vector_store(settings: Settings = Depends(get_settings)) -> VectorStore:
    key = (settings.data_dir, settings.embedding_model)
    store = _vector_stores.get(key)
    if store is None:
        store = VectorStore(settings.data_dir, settings.embedding_model)
        _vector_stores[key] = store
    return store


def reset_store_caches() -> None:
    """Test-only helper: drop cached store singletons so a fresh data_dir gets fresh stores."""
    _metadata_stores.clear()
    _vector_stores.clear()
