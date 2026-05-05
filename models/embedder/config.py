from dataclasses import dataclass

from .base import EmbeddingModel


@dataclass
class EmbedderConfig:
    provider: str = "voyage"
    model:    str = "voyage-3"


def create_embedder(config: EmbedderConfig, input_type: str = "document") -> EmbeddingModel:
    """Instantiate an embedder from config.

    Example:
        embedder = create_embedder(EmbedderConfig(), input_type="query")
        # → VoyageModel(model_name="voyage-3", input_type="query")
    """
    if config.provider == "voyage":
        from .voyage import VoyageModel
        return VoyageModel(model_name=config.model, input_type=input_type)
    raise ValueError(f"Unknown embedder provider: {config.provider!r}")
