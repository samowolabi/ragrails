from .base import EmbeddingModel
from .config import EmbedderConfig, create_embedder
from .registry import EmbedderInfo
from .registry import create_embedder as create_registered_embedder
from .registry import list_embedders, register_embedder

__all__ = [
    "EmbedderConfig",
    "EmbedderInfo",
    "EmbeddingModel",
    "VoyageModel",
    "create_embedder",
    "create_registered_embedder",
    "list_embedders",
    "register_embedder",
]


def __getattr__(name: str):
    if name == "VoyageModel":
        from .voyage import VoyageModel
        return VoyageModel
    raise AttributeError(name)
