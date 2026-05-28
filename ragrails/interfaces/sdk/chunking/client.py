"""SDK methods for chunking."""

from __future__ import annotations

from typing import Any

from ragrails.types import ChunkResult


class ChunkingMixin:
    def chunk(
        self,
        *,
        markdown: str | list[str | dict[str, Any]],
        title: str = "",
        source: str = "",
        chunk_size: int = 2000,
        chunk_overlap: int = 200,
        min_chunk_length: int = 100,
    ) -> ChunkResult:
        """Split markdown text or an array of markdown documents into chunks."""
        self._validate_chunk_args(
            markdown=markdown,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )
        try:
            from ragrails.core.stg_02_chunker.chunker import chunk_markdown_items as _chunk_markdown_items
            from ragrails.core.stg_02_chunker.config import ChunkerConfig
        except ImportError as exc:
            raise RuntimeError("Chunking dependencies are missing. Reinstall with: pip install -U ragrails") from exc

        config = ChunkerConfig(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )
        documents = self._normalize_markdown_documents(markdown, title=title, source=source)
        stats = _chunk_markdown_items(documents, config=config)
        chunks = stats.get("outputs", [])
        return ChunkResult(
            inputs=len(documents),
            chunks=len(chunks),
            items=chunks,
            failed=stats.get("failed", 0),
            errors=stats.get("errors", []),
        )

    @staticmethod
    def _validate_chunk_args(
        *,
        markdown: str | list[str | dict[str, Any]],
        chunk_size: int,
        chunk_overlap: int,
        min_chunk_length: int,
    ) -> None:
        if isinstance(markdown, str):
            if not markdown.strip():
                raise ValueError("markdown must be a non-empty string")
        elif isinstance(markdown, list):
            if not markdown:
                raise ValueError("markdown must include at least one document")
        else:
            raise ValueError("markdown must be a string or a list of markdown documents")
        ChunkingMixin._validate_chunk_numbers(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )

    @staticmethod
    def _normalize_markdown_documents(
        markdown: str | list[str | dict[str, Any]],
        *,
        title: str,
        source: str,
    ) -> list[dict[str, Any]]:
        items = [markdown] if isinstance(markdown, str) else markdown
        documents = []
        for index, item in enumerate(items, start=1):
            if isinstance(item, str):
                if not item.strip():
                    raise ValueError("markdown values must be non-empty strings")
                metadata = {"title": title} if title else {}
                documents.append({
                    "text": item,
                    "source": source or f"document-{index}",
                    "metadata": metadata,
                })
                continue

            if not isinstance(item, dict):
                raise ValueError("markdown list items must be strings or dictionaries")

            text = item.get("text")
            if not isinstance(text, str) or not text.strip():
                raise ValueError("markdown document dictionaries must include non-empty 'text'")

            metadata = dict(item.get("metadata") or {})
            if item.get("title") and "title" not in metadata:
                metadata["title"] = item["title"]
            if title and "title" not in metadata:
                metadata["title"] = title

            documents.append({
                "text": text,
                "source": item.get("source") or source or f"document-{index}",
                "metadata": metadata,
            })
        return documents

    @staticmethod
    def _validate_chunk_numbers(
        *,
        chunk_size: int,
        chunk_overlap: int,
        min_chunk_length: int,
    ) -> None:
        if chunk_size < 1:
            raise ValueError("chunk_size must be greater than 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be greater than or equal to 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if min_chunk_length < 1:
            raise ValueError("min_chunk_length must be greater than 0")
