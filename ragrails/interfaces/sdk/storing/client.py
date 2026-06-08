"""SDK methods for vector storage."""

from __future__ import annotations

from typing import Any, Literal

from ragrails.interfaces.sdk.shared import missing_extra, vector_store_config
from ragrails.types import DeleteResult, EditResult, StoreResult


def validate_vector_store_collection(*, vector_db: str, collection: str | None) -> None:
    if vector_db not in {"qdrant", "qdrant_cloud", "pinecone", "weaviate"}:
        raise ValueError("vector_db must be one of: qdrant, qdrant_cloud, pinecone, weaviate")
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
        vector_db: Literal["qdrant", "qdrant_cloud", "pinecone", "weaviate"] | None = None,
        collection: str | None = None,
        url: str | None = None,
        batch_size: int = 64,
        ensure_collection: bool = True,
        options: dict[str, Any] | None = None,
    ) -> StoreResult:
        """Store embedded chunks in the configured vector database."""
        vector_db, collection, url, options = vector_store_config(
            self,
            vector_db=vector_db,
            collection=collection,
            url=url,
            options=options,
        )
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

    def edit(
        self,
        *,
        chunks: list[dict],
        embedder=None,
        vector_db: Literal["qdrant", "qdrant_cloud", "pinecone", "weaviate"] | None = None,
        collection: str | None = None,
        url: str | None = None,
        batch_size: int = 64,
        options: dict[str, Any] | None = None,
    ) -> EditResult:
        """Edit stored chunks by replacing their text, metadata, and vectors."""
        if embedder is None and hasattr(self, "embedder"):
            embedder = self.embedder(input_type="document")
        vector_db, collection, url, options = vector_store_config(
            self,
            vector_db=vector_db,
            collection=collection,
            url=url,
            options=options,
        )
        self._validate_edit_args(
            chunks=chunks,
            embedder=embedder,
            vector_db=vector_db,
            collection=collection,
            batch_size=batch_size,
            options=options,
        )

        try:
            from ragrails.core.stg_04_storing.lifecycle import edit_stored_chunks
            from ragrails.models.vector_db.registry import create_vector_store

            store = create_vector_store(
                provider=vector_db,
                url=url,
                collection=collection,
                **(options or {}),
            )
            stats = edit_stored_chunks(
                chunks=chunks,
                embedder=embedder,
                store=store,
                batch_size=batch_size,
            )
        except ImportError as exc:
            raise missing_extra("Storage", vector_db, exc)

        return EditResult(
            requested=len(chunks),
            edited=stats["edited"],
            items=stats["outputs"],
            failed=stats["failed"],
            provider=vector_db,
            collection=getattr(store, "collection", collection or ""),
            errors=stats["errors"],
        )

    def delete(
        self,
        *,
        ids: list[str],
        vector_db: Literal["qdrant", "qdrant_cloud", "pinecone", "weaviate"] | None = None,
        collection: str | None = None,
        url: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> DeleteResult:
        """Delete stored chunks by exact chunk IDs."""
        vector_db, collection, url, options = vector_store_config(
            self,
            vector_db=vector_db,
            collection=collection,
            url=url,
            options=options,
        )
        self._validate_delete_args(
            ids=ids,
            vector_db=vector_db,
            collection=collection,
            options=options,
        )

        try:
            from ragrails.core.stg_04_storing.lifecycle import delete_stored_chunks
            from ragrails.models.vector_db.registry import create_vector_store

            store = create_vector_store(
                provider=vector_db,
                url=url,
                collection=collection,
                **(options or {}),
            )
            stats = delete_stored_chunks(ids=ids, store=store)
        except ImportError as exc:
            raise missing_extra("Storage", vector_db, exc)

        return DeleteResult(
            requested=len(ids),
            deleted=stats["deleted"],
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

    @staticmethod
    def _validate_edit_args(
        *,
        chunks: list[dict],
        embedder,
        vector_db: str,
        collection: str | None,
        batch_size: int,
        options: dict[str, Any] | None,
    ) -> None:
        validate_vector_store_collection(vector_db=vector_db, collection=collection)
        if not isinstance(chunks, list):
            raise TypeError("chunks must be a list of chunk dictionaries")
        if not chunks:
            raise ValueError("chunks must include at least one chunk dictionary")
        if (
            not hasattr(embedder, "encode")
            or not callable(embedder.encode)
            or not hasattr(embedder, "vector_size")
        ):
            raise TypeError("embedder must be an embedding model object")
        if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("batch_size must be greater than 0")
        if options is not None and not isinstance(options, dict):
            raise TypeError("options must be a dictionary")

    @staticmethod
    def _validate_delete_args(
        *,
        ids: list[str],
        vector_db: str,
        collection: str | None,
        options: dict[str, Any] | None,
    ) -> None:
        validate_vector_store_collection(vector_db=vector_db, collection=collection)
        if not isinstance(ids, list):
            raise TypeError("ids must be a list of chunk IDs")
        if not ids:
            raise ValueError("ids must include at least one chunk ID")
        if options is not None and not isinstance(options, dict):
            raise TypeError("options must be a dictionary")
