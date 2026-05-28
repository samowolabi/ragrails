from dataclasses import dataclass
from typing import Any

from .base import Reranker
from .registry import create_reranker as create_registered_reranker


@dataclass
class RerankerConfig:
    provider: str = "voyage"
    model: str = "rerank-2-lite"
    options: dict[str, Any] | None = None


def create_reranker(config: RerankerConfig) -> Reranker:
    """Instantiate a reranker from ragrails.config.

    Example:
        reranker = create_reranker(RerankerConfig())
        # → VoyageReranker(model_name="rerank-2-lite")
    """
    return create_registered_reranker(
        config.provider,
        model=config.model,
        **(config.options or {}),
    )
