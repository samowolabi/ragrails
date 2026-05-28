"""Retrieval quality controls for chat."""

from __future__ import annotations

from dataclasses import dataclass

from ragrails.models.vector_db.base import SearchResult


ANSWER_WITH_CAUTION = "answer_with_caution"
ASK_CLARIFYING_QUESTION = "ask_clarifying_question"
REFUSE_GROUNDED_ANSWER = "refuse_grounded_answer"
RETURN_NO_ANSWER = "return_no_answer"

LOW_CONFIDENCE_MODES = {
    ANSWER_WITH_CAUTION,
    ASK_CLARIFYING_QUESTION,
    REFUSE_GROUNDED_ANSWER,
    RETURN_NO_ANSWER,
}


@dataclass(frozen=True)
class RetrievalQualityConfig:
    min_retrieval_score: float = 0.35
    min_rerank_score: float = 0.50
    low_confidence_mode: str = ANSWER_WITH_CAUTION
    max_context_chunks: int | None = None


def filter_by_quality(
    results: list[SearchResult],
    config: RetrievalQualityConfig,
) -> tuple[list[SearchResult], dict]:
    """Filter retrieved chunks and return quality metadata."""
    passed = []
    rejected = []
    for result in results:
        threshold = _threshold_for(result, config)
        score = _score_for(result)
        if score >= threshold:
            passed.append(result)
        else:
            rejected.append(result)

    if config.max_context_chunks is not None:
        passed = passed[:config.max_context_chunks]

    return passed, {
        "status": "pass" if passed else "low_confidence",
        "mode": config.low_confidence_mode if not passed else "",
        "input_chunks": len(results),
        "passed_chunks": len(passed),
        "rejected_chunks": len(rejected),
        "min_retrieval_score": config.min_retrieval_score,
        "min_rerank_score": config.min_rerank_score,
    }


def validate_quality_config(config: RetrievalQualityConfig) -> dict | None:
    if isinstance(config.min_retrieval_score, bool) or not isinstance(config.min_retrieval_score, (int, float)):
        return _failure("min_retrieval_score must be a number")
    if isinstance(config.min_rerank_score, bool) or not isinstance(config.min_rerank_score, (int, float)):
        return _failure("min_rerank_score must be a number")
    if config.low_confidence_mode not in LOW_CONFIDENCE_MODES:
        return _failure(f"low_confidence_mode must be one of: {', '.join(sorted(LOW_CONFIDENCE_MODES))}")
    if config.max_context_chunks is not None and (
        isinstance(config.max_context_chunks, bool)
        or not isinstance(config.max_context_chunks, int)
        or config.max_context_chunks < 1
    ):
        return _failure("max_context_chunks must be greater than 0 or None")
    return None


def _score_for(result: SearchResult) -> float:
    return result.rerank_score if result.rerank_score is not None else result.score


def _threshold_for(result: SearchResult, config: RetrievalQualityConfig) -> float:
    return config.min_rerank_score if result.rerank_score is not None else config.min_retrieval_score


def _failure(error: str) -> dict:
    return {
        "source": "",
        "source_kind": "chat",
        "stage": "quality",
        "error": error,
        "isRetryable": False,
        "attempts": 1,
    }
