from dataclasses import dataclass
from typing import Any

from .base import EmbeddingModel
from .registry import create_embedder as create_registered_embedder


@dataclass
class EmbedderConfig:
    provider: str = "voyage"
    model: str = "voyage-3"
    options: dict[str, Any] | None = None


def create_embedder(config: EmbedderConfig, input_type: str = "document") -> EmbeddingModel:
    """Instantiate an embedder from ragrails.config.

    Example:
        embedder = create_embedder(EmbedderConfig(), input_type="query")
        # → VoyageModel(model_name="voyage-3", input_type="query")
    """
    return create_registered_embedder(
        config.provider,
        model=config.model,
        input_type=input_type,
        **(config.options or {}),
    )
