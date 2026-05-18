"""Public Python SDK interface for Ragrails."""

from __future__ import annotations

from .chunking import ChunkingMixin
from .embedding import EmbeddingMixin
from .ingestion import IngestionMixin
from .retrieval import RetrievalMixin
from .storing import StoringMixin


class RagRails(IngestionMixin, ChunkingMixin, EmbeddingMixin, StoringMixin, RetrievalMixin):
    """Main public SDK client.

    Example:
        from ragrails import RagRails

        result = RagRails().scrape(
            url=["https://example.com"],
            mode="full",
            output_dir="files/output/web_crawled",
        )
    """


__all__ = ["RagRails"]
