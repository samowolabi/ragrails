from .base import Reranker

__all__ = ["Reranker", "VoyageReranker"]


def __getattr__(name: str):
    if name == "VoyageReranker":
        from .voyage import VoyageReranker
        return VoyageReranker
    raise AttributeError(name)
