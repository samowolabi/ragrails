from dataclasses import dataclass

from .base import VectorStore
from .registry import create_vector_store


@dataclass
class VectorStoreConfig:
    provider: str = "qdrant"
    url: str = ""
    collection: str = ""


def create_store(config: VectorStoreConfig) -> VectorStore:
    return create_vector_store(
        provider=config.provider,
        url=config.url,
        collection=config.collection,
    )
