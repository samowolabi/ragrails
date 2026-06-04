"""Public Python SDK interface for Ragrails."""

from __future__ import annotations

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

        result = RagRails().scrape(
            url=["https://example.com"],
            mode="full",
        )
    """


__all__ = ["RagRails"]
