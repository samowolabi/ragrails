from __future__ import annotations

import re

from ragrails.models.vector_db.base import SearchResult


def select_context(results: list[SearchResult], *, min_score: float = 0.0, max_chunks: int | None = None) -> list[SearchResult]:
    selected = [
        result for result in results
        if _context_score(result) >= min_score
    ]
    if max_chunks is not None:
        return selected[:max_chunks]
    return selected


def build_context(results: list[SearchResult]) -> str:
    blocks = []
    for index, result in enumerate(results, start=1):
        citation_id = citation_id_for(index)
        metadata = result.metadata or {}
        title = metadata.get("title", "")
        heading = _heading_text(metadata.get("heading", ""))
        path = metadata.get("path") or metadata.get("source", "")

        header = f"[{citation_id}]"
        if title:
            header += f" {title}"
        if heading:
            header += f" - {heading}"
        if path:
            header += f"\n{path}"

        blocks.append(f"{header}\n\n{result.text}")
    return "\n\n---\n\n".join(blocks)


def extract_sources(results: list[SearchResult]) -> list[dict]:
    sources = []
    for index, result in enumerate(results, start=1):
        metadata = result.metadata or {}
        sources.append({
            "id": citation_id_for(index),
            "chunk_id": metadata.get("chunk_id") or result.id,
            "title": metadata.get("title", ""),
            "heading": _heading_text(metadata.get("heading", "")),
            "path": metadata.get("path") or metadata.get("source", ""),
            "retrieval_score": result.score,
            "rerank_score": result.rerank_score,
        })
    return sources


def validate_citations(answer: str, sources: list[dict]) -> str:
    valid_ids = {source["id"] for source in sources}

    def replace(match: re.Match) -> str:
        citation = match.group(1)
        return f"[{citation}]" if citation in valid_ids else f"[invalid:{citation}]"

    return re.sub(r"\[(C\d+)\]", replace, answer)


def citation_id_for(index: int) -> str:
    return f"C{index}"


def _context_score(result: SearchResult) -> float:
    return result.rerank_score if result.rerank_score is not None else result.score


def _heading_text(heading) -> str:
    if isinstance(heading, dict):
        return " > ".join(str(value) for value in heading.values() if value)
    return str(heading or "")
