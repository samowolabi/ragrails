"""Public Python SDK interface for Ragrails."""

from __future__ import annotations

from typing import Any

from .chat import ChatMixin
from .chunking import ChunkingMixin
from .embedding import EmbeddingMixin
from .ingestion import IngestionMixin
from .pipeline import PipelineMixin
from .retrieval import RetrievalMixin
from .storing import StoringMixin


class RagRails(IngestionMixin, ChunkingMixin, EmbeddingMixin, StoringMixin, RetrievalMixin, ChatMixin, PipelineMixin):
    """Main public SDK client.

    Example:
        from ragrails import RagRails

        rag = RagRails(
            collection="docs",
            vector_store={"provider": "qdrant", "url": "http://localhost:6333"},
            embedding={"provider": "voyage", "model": "voyage-3"},
            llm={"provider": "openai", "model": "gpt-5.5"},
        )

        result = rag.query("What does this knowledge base cover?")
    """

    def __init__(
        self,
        *,
        collection: str | None = None,
        vector_store: dict[str, Any] | None = None,
        embedding: dict[str, Any] | None = None,
        llm: dict[str, Any] | None = None,
        reranker: dict[str, Any] | None = None,
    ) -> None:
        self._validate_default_group("vector_store", vector_store)
        self._validate_default_group("embedding", embedding)
        self._validate_default_group("llm", llm)
        self._validate_default_group("reranker", reranker)
        if collection is not None and not isinstance(collection, str):
            raise TypeError("collection must be a string")

        vector_config = self._clean_default_group(vector_store)
        if collection is not None:
            vector_config["collection"] = collection

        self._sdk_defaults: dict[str, dict[str, Any]] = {
            "vector_store": vector_config,
            "embedding": self._clean_default_group(embedding),
            "llm": self._clean_default_group(llm),
            "reranker": self._clean_default_group(reranker),
        }
        self._sdk_cache: dict[tuple[str, tuple[tuple[str, str], ...]], object] = {}

    def _sdk_config(self, name: str) -> dict[str, Any]:
        return dict(self._sdk_defaults.get(name, {}))

    def _sdk_object(self, name: str, factory):
        config = self._sdk_config(name)
        if not config:
            return None
        enabled = config.pop("enabled", None)
        if enabled is False:
            return None
        key = (name, tuple(sorted((str(k), repr(v)) for k, v in config.items())))
        if key not in self._sdk_cache:
            self._sdk_cache[key] = factory(config)
        return self._sdk_cache[key]

    @staticmethod
    def _validate_default_group(name: str, value: dict[str, Any] | None) -> None:
        if value is not None and not isinstance(value, dict):
            raise TypeError(f"{name} must be a dictionary")

    @staticmethod
    def _clean_default_group(value: dict[str, Any] | None) -> dict[str, Any]:
        return {key: item for key, item in dict(value or {}).items() if item is not None}


__all__ = ["RagRails"]
