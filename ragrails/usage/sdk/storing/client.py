"""SDK methods for vector storage."""

from __future__ import annotations

from typing import Literal

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
        input_dir: str = "files/output/chunks",
        vector_db: Literal["qdrant", "pinecone", "weaviate"] = "qdrant",
        collection: str | None = None,
        url: str | None = None,
        files: str | list[str] | None = None,
        batch_size: int = 64,
        embedder: str = "voyage",
        model: str = "voyage-3",
    ) -> StoreResult:
        """Embed chunk JSON files and store them in the configured vector DB."""
        result = self.embed(
            input_dir=input_dir,
            vector_db=vector_db,
            collection=collection,
            url=url,
            files=files,
            batch_size=batch_size,
            embedder=embedder,
            model=model,
        )
        return StoreResult(
            files=result.files,
            chunks=result.chunks,
            input_dir=result.input_dir,
            provider=result.provider,
            collection=result.collection,
            errors=result.errors,
        )
