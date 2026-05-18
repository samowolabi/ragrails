"""SDK methods for embedding chunks into vector databases."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from ragrails.types import EmbedResult
from ragrails.usage.sdk.shared import missing_extra
from ragrails.usage.sdk.storing.client import validate_vector_store_collection


class EmbeddingMixin:
    def embed(
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
    ) -> EmbedResult:
        """Embed chunk JSON files and upsert them into a vector database."""
        normalized_files = self._normalize_embed_files(files)
        self._validate_embed_args(
            input_dir=input_dir,
            vector_db=vector_db,
            collection=collection,
            files=normalized_files,
            batch_size=batch_size,
            embedder=embedder,
            model=model,
        )

        install_extra = f"store-{vector_db}" if embedder == "voyage" else f"{embedder},{vector_db}"
        try:
            from ragrails.models.embedder.config import EmbedderConfig as ModelEmbedderConfig
            from ragrails.models.embedder.config import create_embedder
            from ragrails.models.vector_db.registry import create_vector_store
            from ragrails.pipeline.stg_03_embedder.config import EmbedderConfig as StoreConfig
            from ragrails.pipeline.stg_03_embedder.embedder import embed_chunks

            embedding_model = create_embedder(
                ModelEmbedderConfig(provider=embedder, model=model),
                input_type="document",
            )
            vector_store = create_vector_store(
                provider=vector_db,
                url=url,
                collection=collection,
            )
            stats = embed_chunks(
                model=embedding_model,
                store=vector_store,
                config=StoreConfig(batch_size=batch_size, input_type="document", input_dir=input_dir),
                files=normalized_files,
            )
        except ImportError as exc:
            raise missing_extra("Embedding", install_extra, exc)

        return EmbedResult(
            files=stats["files"],
            chunks=stats["chunks"],
            input_dir=stats["input_dir"],
            provider=stats["provider"],
            collection=stats["collection"],
            errors=stats["errors"],
        )

    @staticmethod
    def _normalize_embed_files(files: str | list[str] | None) -> list[str] | None:
        if files is None:
            return None
        normalized = [files] if isinstance(files, str) else list(files)
        if not normalized:
            raise ValueError("files must include at least one chunk JSON filename")
        for filename in normalized:
            if not isinstance(filename, str) or not filename.strip():
                raise ValueError("files values must be non-empty strings")
        return normalized

    @staticmethod
    def _validate_embed_args(
        *,
        input_dir: str,
        vector_db: str,
        collection: str | None,
        files: list[str] | None,
        batch_size: int,
        embedder: str,
        model: str,
    ) -> None:
        validate_vector_store_collection(vector_db=vector_db, collection=collection)
        if not input_dir:
            raise ValueError("input_dir is required")
        if batch_size < 1:
            raise ValueError("batch_size must be greater than 0")
        if not embedder:
            raise ValueError("embedder is required")
        if not model:
            raise ValueError("model is required")

        base = Path(input_dir)
        if not base.exists():
            raise FileNotFoundError(f"Embed input directory not found: {input_dir}")
        if not base.is_dir():
            raise NotADirectoryError(f"Embed input path is not a directory: {input_dir}")

        paths = [base / filename for filename in files] if files else sorted(base.glob("*.json"))
        if not paths:
            raise ValueError(f"No chunk JSON files found in input_dir: {input_dir}")
        for path in paths:
            if path.suffix.lower() != ".json":
                raise ValueError(f"Embed input file must be JSON: {path.name}")
            if not path.exists():
                raise FileNotFoundError(f"Embed input file not found: {path}")
            if not path.is_file():
                raise IsADirectoryError(f"Embed input path is not a file: {path}")
