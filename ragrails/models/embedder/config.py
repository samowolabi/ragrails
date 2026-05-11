from dataclasses import dataclass

from .base import EmbeddingModel


@dataclass
class EmbedderConfig:
    provider: str = "voyage"
    model:    str = "voyage-3"


def create_embedder(config: EmbedderConfig, input_type: str = "document") -> EmbeddingModel:
    """Instantiate an embedder from ragrails.config.

    Example:
        embedder = create_embedder(EmbedderConfig(), input_type="query")
        # → VoyageModel(model_name="voyage-3", input_type="query")
    """
    if config.provider == "voyage":
        try:
            from .voyage import VoyageModel
            return VoyageModel(model_name=config.model, input_type=input_type)
        except ImportError as exc:
            raise RuntimeError('Voyage embeddings require: pip install "ragrails[voyage]"') from exc
    raise ValueError(f"Unknown embedder provider: {config.provider!r}")
