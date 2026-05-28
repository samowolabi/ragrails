"""SDK chat feature configuration objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoryCompactionConfig:
    enabled: bool = True
    history_limit: int | None = 15
    keep_recent: int = 5


@dataclass(frozen=True)
class QueryRewriteConfig:
    enabled: bool = False
    rewrite_context: str = ""
    session_context: str = ""


@dataclass(frozen=True)
class IntentRoutingConfig:
    enabled: bool = True


@dataclass(frozen=True)
class ChatRetrievalQualityConfig:
    min_retrieval_score: float = 0.35
    min_rerank_score: float = 0.50
    low_confidence_mode: str = "answer_with_caution"
    max_context_chunks: int | None = None
