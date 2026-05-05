from dataclasses import dataclass

from .base import Reranker


@dataclass
class RerankerConfig:
    provider: str = "voyage"
    model:    str = "rerank-2-lite"


def create_reranker(config: RerankerConfig) -> Reranker:
    """Instantiate a reranker from config.

    Example:
        reranker = create_reranker(RerankerConfig())
        # → VoyageReranker(model_name="rerank-2-lite")
    """
    if config.provider == "voyage":
        from .voyage import VoyageReranker
        return VoyageReranker(model_name=config.model)
    raise ValueError(f"Unknown reranker provider: {config.provider!r}")
