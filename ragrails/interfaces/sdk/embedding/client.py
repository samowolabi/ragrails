"""SDK methods for embedding chunks in memory."""

from __future__ import annotations

from typing import Any

from ragrails.interfaces.sdk.shared import configured, merge_config, missing_extra
from ragrails.types import EmbedResult


class EmbeddingMixin:
    def embedder(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        input_type: str = "document",
        options: dict[str, Any] | None = None,
    ):
        """Create an embedding model object."""
        defaults = configured(self, "embedding")
        config = merge_config(defaults, {
            "provider": provider,
            "model": model,
            "input_type": input_type,
            "options": options,
        })
        provider = config.get("provider", "voyage")
        model = config.get("model", "voyage-3")
        input_type = config.get("input_type", "document")
        options = config.get("options")
        self._validate_embedder_args(
            provider=provider,
            model=model,
            input_type=input_type,
            options=options,
        )

        try:
            from ragrails.models.embedder.config import EmbedderConfig as ModelEmbedderConfig
            from ragrails.models.embedder.config import create_embedder

            return create_embedder(
                ModelEmbedderConfig(provider=provider, model=model, options=options),
                input_type=input_type,
            )
        except ImportError as exc:
            raise missing_extra("Embedding", provider, exc)

    def embed(
        self,
        *,
        chunks: list[dict],
        embedder=None,
        input_type: str = "document",
        batch_size: int = 64,
    ) -> EmbedResult:
        """Embed chunk dictionaries and return embedded chunks in memory."""
        if embedder is None:
            embedder = self.embedder(input_type=input_type)
        self._validate_embed_args(
            chunks=chunks,
            embedder=embedder,
            batch_size=batch_size,
        )

        try:
            from ragrails.core.stg_03_embedder.config import EmbedderConfig as StoreConfig
            from ragrails.core.stg_03_embedder.embedder import embed_chunks

            stats = embed_chunks(
                chunks=chunks,
                model=embedder,
                config=StoreConfig(batch_size=batch_size),
            )
        except ImportError as exc:
            raise missing_extra("Embedding", "embedder", exc)

        return EmbedResult(
            inputs=len(chunks),
            embedded=stats["embedded"],
            items=stats["outputs"],
            failed=stats["failed"],
            errors=stats["errors"],
        )

    @staticmethod
    def _validate_embed_args(
        *,
        chunks: list[dict],
        embedder,
        batch_size: int,
    ) -> None:
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

    @staticmethod
    def _validate_embedder_args(
        *,
        provider: str,
        model: str,
        input_type: str,
        options: dict[str, Any] | None,
    ) -> None:
        if not isinstance(provider, str) or not provider.strip():
            raise ValueError("provider is required")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model is required")
        if not isinstance(input_type, str) or not input_type.strip():
            raise ValueError("input_type is required")
        if options is not None and not isinstance(options, dict):
            raise TypeError("options must be a dictionary")
