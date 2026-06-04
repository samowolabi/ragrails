"""Public SDK result types."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DLQ:
    """Dead-letter queue for retryable scrape failures.

    Pass to ``scrape()`` to track or retry failed URLs.

    Example::

        # Track failures in response
        result = rag.scrape("https://example.com/docs", dlq=DLQ())
        result.dlq.items   # list of retry input dicts

        # Save failures to file
        result = rag.scrape("https://example.com/docs", dlq=DLQ("files/dlq/web.json"))

        # Retry from previous result
        result = rag.scrape(dlq=result.dlq)

        # Retry from file path
        result = rag.scrape(dlq="files/dlq/web.json")
    """

    path: str | None = None
    items: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class ScrapeResult:
    """Summary returned by `RagRails().scrape(...)`."""

    pages: int
    failed: int
    outputs: list[dict]
    errors: list[dict]
    dlq: DLQ | None = None


@dataclass(frozen=True)
class ParseResult:
    """Summary returned by `RagRails().parse(...)`."""

    documents: int
    failed: int
    outputs: list[dict]
    errors: list[dict]


@dataclass(frozen=True)
class ApiIngestResult:
    """Summary returned by `RagRails().fetch(...)`."""

    documents: int
    failed: int
    outputs: list[dict]
    errors: list[dict]


@dataclass(frozen=True)
class ChunkResult:
    """Summary returned by `RagRails().chunk(...)`."""

    inputs: int
    chunks: int
    items: list[dict]
    failed: int
    errors: list[str]


@dataclass(frozen=True)
class StoreResult:
    """Summary returned by `RagRails().store(...)`."""

    inputs: int
    stored: int
    items: list[dict]
    failed: int
    provider: str
    collection: str
    errors: list[dict]


@dataclass(frozen=True)
class IngestPipelineResult:
    """Summary returned by `RagRails().ingest(...)`."""

    sources: int
    chunks: int
    embedded: int
    stored: int
    source_results: dict[str, object]
    chunk_result: ChunkResult
    embed_result: EmbedResult
    store_result: StoreResult
    failed: int
    errors: list[dict]


@dataclass(frozen=True)
class EditResult:
    """Summary returned by `RagRails().edit(...)`."""

    requested: int
    edited: int
    items: list[dict]
    failed: int
    provider: str
    collection: str
    errors: list[dict]


@dataclass(frozen=True)
class DeleteResult:
    """Summary returned by `RagRails().delete(...)`."""

    requested: int
    deleted: int
    items: list[dict]
    failed: int
    provider: str
    collection: str
    errors: list[dict]


@dataclass(frozen=True)
class EmbedResult:
    """Summary returned by `RagRails().embed(...)`."""

    inputs: int
    embedded: int
    items: list[dict]
    failed: int
    errors: list[dict]


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
    search_query: str
    retrieved: int
    items: list[RetrievedChunk]
    failed: int
    errors: list[dict]


@dataclass(frozen=True)
class ChatResult:
    """Summary returned by `RagRails().chat(...)`."""

    answer: str
    sources: list[dict]
    history: list[dict]
    retrieval: dict
    llm: dict
    errors: list[dict]
    retrieval_quality: dict
    answer_confidence: dict
    compacted: bool = False
    intent: str = "rag"
