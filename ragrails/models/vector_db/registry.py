from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module

from .base import VectorStore
from .types import VectorStoreInfo


VectorStoreFactory = Callable[..., VectorStore]


@dataclass(frozen=True)
class _VectorStoreSpec:
    info: VectorStoreInfo
    factory: VectorStoreFactory | str


VECTOR_STORE_SPECS: dict[str, _VectorStoreSpec] = {
    "qdrant": _VectorStoreSpec(
        info=VectorStoreInfo(
            provider="qdrant",
            default_url="http://localhost:6333",
            default_collection="rag_chunks",
        ),
        factory="ragrails.models.vector_db.qdrant:QdrantStore",
    ),
    "qdrant_cloud": _VectorStoreSpec(
        info=VectorStoreInfo(
            provider="qdrant_cloud",
            default_url="",
            default_collection="rag_chunks",
        ),
        factory=lambda **kwargs: _qdrant_cloud_store(**kwargs),
    ),
    "pinecone": _VectorStoreSpec(
        info=VectorStoreInfo(
            provider="pinecone",
            default_url="",
            default_collection="rag-chunks",
        ),
        factory="ragrails.models.vector_db.pinecone:PineconeStore",
    ),
    "weaviate": _VectorStoreSpec(
        info=VectorStoreInfo(
            provider="weaviate",
            default_url="http://localhost:8080",
            default_collection="RagChunks",
        ),
        factory="ragrails.models.vector_db.weaviate:WeaviateStore",
    ),
}


def list_vector_stores() -> list[VectorStoreInfo]:
    return [spec.info for spec in VECTOR_STORE_SPECS.values()]


def register_vector_store(
    provider: str,
    factory: VectorStoreFactory,
    *,
    default_url: str = "",
    default_collection: str,
    replace: bool = False,
) -> None:
    if not provider:
        raise ValueError("provider is required")
    if provider in VECTOR_STORE_SPECS and not replace:
        raise ValueError(f"Vector DB provider already registered: {provider!r}")

    VECTOR_STORE_SPECS[provider] = _VectorStoreSpec(
        info=VectorStoreInfo(
            provider=provider,
            default_url=default_url,
            default_collection=default_collection,
        ),
        factory=factory,
    )


def create_vector_store(
    provider: str = "qdrant",
    *,
    url: str | None = None,
    collection: str | None = None,
    **options,
) -> VectorStore:
    if provider not in VECTOR_STORE_SPECS:
        available = ", ".join(sorted(VECTOR_STORE_SPECS))
        raise ValueError(f"Unknown vector DB provider '{provider}'. Available providers: {available}")

    spec = VECTOR_STORE_SPECS[provider]
    info = spec.info
    factory = _load_factory(spec.factory)
    return factory(
        url=url or info.default_url,
        collection=collection or info.default_collection,
        **options,
    )


def _load_factory(factory: object) -> VectorStoreFactory:
    if callable(factory):
        return factory
    if not isinstance(factory, str):
        raise TypeError("vector store factory must be a callable or import path")

    module_name, class_name = factory.split(":", 1)
    module = import_module(module_name)
    return getattr(module, class_name)


def _qdrant_cloud_store(**kwargs) -> VectorStore:
    from .qdrant import QdrantStore

    return QdrantStore(provider="qdrant_cloud", **kwargs)
