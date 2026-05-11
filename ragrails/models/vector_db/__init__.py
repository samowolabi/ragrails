from .base import Point, SearchResult, VectorStore
from .config import VectorStoreConfig, create_store
from .registry import create_vector_store, list_vector_stores
from .types import VectorStoreInfo

__all__ = [
    "Point",
    "SearchResult",
    "VectorStore",
    "PineconeStore",
    "QdrantStore",
    "WeaviateStore",
    "VectorStoreConfig",
    "VectorStoreInfo",
    "create_store",
    "create_vector_store",
    "list_vector_stores",
]


def __getattr__(name: str):
    if name == "QdrantStore":
        from .qdrant import QdrantStore
        return QdrantStore
    if name == "PineconeStore":
        from .pinecone import PineconeStore
        return PineconeStore
    if name == "WeaviateStore":
        from .weaviate import WeaviateStore
        return WeaviateStore
    raise AttributeError(name)
