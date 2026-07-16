"""Shared FastAPI dependencies: settings, auth, and service singletons.

Store instances are cached by data_dir (and, for the vector store, embedding_model) rather than
via functools.lru_cache on a zero-arg call, so that the FastAPI dependency-override mechanism
used in tests (overriding get_settings) is honored - each distinct data_dir gets its own
singleton. This is the "initialized store singleton" global state permitted by docs/rules.md.
"""

import hmac

from fastapi import Depends, Header

from app.config import Settings, get_settings
from app.errors import UnauthorizedError
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


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    """Enforce X-API-Key on data routes when API_KEY is configured; open when unset.

    Comparison is constant-time. Never logs the key or the header value.
    """
    if not settings.api_key:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise UnauthorizedError("Missing or invalid API key.")
