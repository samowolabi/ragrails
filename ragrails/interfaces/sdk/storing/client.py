"""SDK methods for vector storage."""

from __future__ import annotations

from typing import Any, Literal

from ragrails.interfaces.sdk.shared import missing_extra
from ragrails.types import StoreResult


def validate_vector_store_collection(*, vector_db: str, collection: str | None) -> None:
    if vector_db not in {"qdrant", "pinecone", "weaviate"}:
        raise ValueError("vector_db must be one of: qdrant, pinecone, weaviate")
    if vector_db == "pinecone" and collection and "_" in collection:
        raise ValueError("Pinecone collection/index names cannot contain underscores. Use hyphens, e.g. 'rag-chunks'.")
    if vector_db == "weaviate" and collection and not collection.isalnum():
        raise ValueError("Weaviate collection names must contain only letters and digits, e.g. 'RagChunks'.")
    if vector_db == "weaviate" and collection and not collection[:1].isupper():
        raise ValueError("Weaviate collection names must start with an uppercase letter, e.g. 'RagChunks'.")


class StoringMixin:
    def store(
        self,
        *,
        embedded_chunks: list[dict],
        vector_db: Literal["qdrant", "pinecone", "weaviate"] = "qdrant",
        collection: str | None = None,
        url: str | None = None,
        batch_size: int = 64,
        ensure_collection: bool = True,
        options: dict[str, Any] | None = None,
    ) -> StoreResult:
        """Store embedded chunks in the configured vector database."""
        self._validate_store_args(
            embedded_chunks=embedded_chunks,
            vector_db=vector_db,
            collection=collection,
            batch_size=batch_size,
            ensure_collection=ensure_collection,
            options=options,
        )

        try:
            from ragrails.core.stg_04_storing.config import StoringConfig
            from ragrails.core.stg_04_storing.storing import store_embeddings
            from ragrails.models.vector_db.registry import create_vector_store

            store = create_vector_store(
                provider=vector_db,
                url=url,
                collection=collection,
                **(options or {}),
            )
            stats = store_embeddings(
                embedded_chunks=embedded_chunks,
                store=store,
                config=StoringConfig(batch_size=batch_size, ensure_collection=ensure_collection),
            )
        except ImportError as exc:
            raise missing_extra("Storage", vector_db, exc)

        return StoreResult(
            inputs=len(embedded_chunks),
            stored=stats["stored"],
            items=stats["outputs"],
            failed=stats["failed"],
            provider=vector_db,
            collection=getattr(store, "collection", collection or ""),
            errors=stats["errors"],
        )

    @staticmethod
    def _validate_store_args(
        *,
        embedded_chunks: list[dict],
        vector_db: str,
        collection: str | None,
        batch_size: int,
        ensure_collection: bool,
        options: dict[str, Any] | None,
    ) -> None:
        validate_vector_store_collection(vector_db=vector_db, collection=collection)
        if not isinstance(embedded_chunks, list):
            raise TypeError("embedded_chunks must be a list of embedded chunk dictionaries")
        if not embedded_chunks:
            raise ValueError("embedded_chunks must include at least one embedded chunk dictionary")
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("batch_size must be greater than 0")
        if not isinstance(ensure_collection, bool):
            raise TypeError("ensure_collection must be a boolean")
        if options is not None and not isinstance(options, dict):
            raise TypeError("options must be a dictionary")
