"""Small, local-only RAG trace objects for the `/debug` command."""

from dataclasses import dataclass, field

from ragrails.models.vector_db.base import SearchResult


@dataclass
class TraceChunk:
    """Compact snapshot of one retrieved chunk.

    The debug command should be useful in a terminal without dumping the full
    retrieved document text, so each chunk keeps scores, source metadata, and a
    short preview.
    """

    id: str
    retrieval_score: float
    rerank_score: float | None
    title: str
    path: str
    heading: str
    preview: str


@dataclass
class RagDebugTrace:
    """Local trace for the most recent chat turn.

    This is populated by the pipeline and read by `/debug`. It is never sent to
    the LLM and is not appended to multi-turn conversation history.
    """

    original_query: str
    rewritten_query: str = ""
    conversational: bool = False
    retrieval_top_k: int = 0
    retrieval_candidate_k: int = 0
    min_retrieval_score: float = 0.0
    min_rerank_score: float = 0.0
    retrieval_skipped_reason: str = ""
    retrieval_error: str = ""
    generation_mode: str = ""
    model: str = ""
    provider: str = ""
    stream: bool = False
    tools_enabled: bool = False
    candidates: list[TraceChunk] = field(default_factory=list)
    ranked: list[TraceChunk] = field(default_factory=list)
    used: list[TraceChunk] = field(default_factory=list)


def snapshot_results(results: list[SearchResult], limit: int | None = None) -> list[TraceChunk]:
    """Create compact debug snapshots from search results."""
    selected = results[:limit] if limit is not None else results
    return [_snapshot_result(result) for result in selected]


def _snapshot_result(result: SearchResult) -> TraceChunk:
    heading = result.metadata.get("heading", {})
    heading_text = " > ".join(heading.values()) if isinstance(heading, dict) else str(heading or "")
    preview = " ".join(result.text.split())
    if len(preview) > 220:
        preview = preview[:217] + "..."

    return TraceChunk(
        id=result.id,
        retrieval_score=result.score,
        rerank_score=result.rerank_score,
        title=result.metadata.get("title", ""),
        path=result.metadata.get("path", ""),
        heading=heading_text,
        preview=preview,
    )
