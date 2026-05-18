"""Public SDK result types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScrapeResult:
    """Summary returned by `RagRails().scrape(...)`."""

    pages: int
    failed: int
    output_dir: str
    files: list[str]
    dlq_path: str
    errors: list[str]


@dataclass(frozen=True)
class ParseResult:
    """Summary returned by `RagRails().parse(...)`."""

    documents: int
    failed: int
    output_dir: str
    files: list[str]
    errors: list[str]


@dataclass(frozen=True)
class ApiIngestResult:
    """Summary returned by `RagRails().fetch(...)`."""

    pages: int
    items: int
    failed: int
    output_dir: str
    files: list[str]
    errors: list[str]


@dataclass(frozen=True)
class ChunkResult:
    """Summary returned by `RagRails().chunk(...)`."""

    files: int
    chunks: int
    output_dir: str
    output_files: list[str]
    failed: int
    errors: list[str]


@dataclass(frozen=True)
class StoreResult:
    """Summary returned by `RagRails().store(...)`."""

    files: int
    chunks: int
    input_dir: str
    provider: str
    collection: str
    errors: list[str]


@dataclass(frozen=True)
class EmbedResult:
    """Summary returned by `RagRails().embed(...)`."""

    files: int
    chunks: int
    input_dir: str
    provider: str
    collection: str
    errors: list[str]


@dataclass(frozen=True)
class RetrievedChunk:
    """One retrieved chunk returned by `RagRails().retrieve(...)`."""

    id: str
    score: float
    text: str
    metadata: dict
    rerank_score: float | None = None


@dataclass(frozen=True)
class RetrieveResult:
    """Summary returned by `RagRails().retrieve(...)`."""

    query: str
    results: list[RetrievedChunk]
