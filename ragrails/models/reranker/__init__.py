from .base import Reranker
from .config import RerankerConfig, create_reranker
from .registry import RerankerInfo
from .registry import create_reranker as create_registered_reranker
from .registry import list_rerankers, register_reranker

__all__ = [
    "BM25Reranker",
    "Reranker",
    "RerankerConfig",
    "RerankerInfo",
    "VoyageReranker",
    "create_reranker",
    "create_registered_reranker",
    "list_rerankers",
    "register_reranker",
]


def __getattr__(name: str):
    if name == "BM25Reranker":
        from .bm25 import BM25Reranker
        return BM25Reranker
    if name == "VoyageReranker":
        from .voyage import VoyageReranker
        return VoyageReranker
    raise AttributeError(name)
