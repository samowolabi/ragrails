from dataclasses import dataclass

from .base import Reranker


@dataclass
class RerankerConfig:
    provider: str = "voyage"
    model:    str = "rerank-2-lite"


def create_reranker(config: RerankerConfig) -> Reranker:
    """Instantiate a reranker from ragrails.config.

    Example:
        reranker = create_reranker(RerankerConfig())
        # → VoyageReranker(model_name="rerank-2-lite")
    """
    if config.provider == "voyage":
        try:
            from .voyage import VoyageReranker
            return VoyageReranker(model_name=config.model)
        except ImportError as exc:
            raise RuntimeError('Reranking requires: pip install "ragrails[rerank]"') from exc
    raise ValueError(f"Unknown reranker provider: {config.provider!r}")
