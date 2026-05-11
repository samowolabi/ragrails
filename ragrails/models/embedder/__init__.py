from .base import EmbeddingModel

__all__ = ["EmbeddingModel", "VoyageModel"]


def __getattr__(name: str):
    if name == "VoyageModel":
        from .voyage import VoyageModel
        return VoyageModel
    raise AttributeError(name)
