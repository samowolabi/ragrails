"""Answer confidence metadata for chat."""

from __future__ import annotations


def build_answer_confidence(*, retrieval_quality: dict, sources: list[dict], intent: str, errors: list[dict]) -> dict:
    """Derive answer confidence from retrieval quality and sources."""
    if errors:
        return {
            "level": "none",
            "reason": "errors",
            "signals": _signals(retrieval_quality=retrieval_quality, sources=sources),
        }

    if retrieval_quality.get("status") == "skipped":
        return {
            "level": "medium",
            "reason": retrieval_quality.get("reason", "not_retrieval_based"),
            "signals": _signals(retrieval_quality=retrieval_quality, sources=sources),
        }

    if retrieval_quality.get("status") == "low_confidence":
        return {
            "level": "low",
            "reason": f"low_confidence:{retrieval_quality.get('mode', '')}",
            "signals": _signals(retrieval_quality=retrieval_quality, sources=sources),
        }

    passed_chunks = int(retrieval_quality.get("passed_chunks") or len(sources))
    best_score = _best_effective_score(sources)
    if passed_chunks >= 2 and best_score >= 0.75:
        level = "high"
    elif passed_chunks >= 1:
        level = "medium"
    else:
        level = "low"

    return {
        "level": level,
        "reason": "retrieval_quality_pass",
        "signals": _signals(retrieval_quality=retrieval_quality, sources=sources),
    }


def _signals(*, retrieval_quality: dict, sources: list[dict]) -> dict:
    return {
        "retrieval_quality_status": retrieval_quality.get("status", "not_evaluated"),
        "low_confidence_mode": retrieval_quality.get("mode", ""),
        "passed_chunks": retrieval_quality.get("passed_chunks", len(sources)),
        "source_count": len(sources),
        "best_retrieval_score": _best_score(sources, "retrieval_score"),
        "best_rerank_score": _best_score(sources, "rerank_score"),
    }


def _best_effective_score(sources: list[dict]) -> float:
    scores = []
    for source in sources:
        if source.get("rerank_score") is not None:
            scores.append(float(source["rerank_score"]))
        elif source.get("retrieval_score") is not None:
            scores.append(float(source["retrieval_score"]))
    return max(scores, default=0.0)


def _best_score(sources: list[dict], key: str) -> float | None:
    scores = [float(source[key]) for source in sources if source.get(key) is not None]
    return max(scores) if scores else None
