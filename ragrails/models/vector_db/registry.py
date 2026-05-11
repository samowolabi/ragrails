from importlib import import_module

from .base import VectorStore
from .types import VectorStoreInfo


VECTOR_STORE_SPECS = {
    "qdrant": {
        "info": VectorStoreInfo(
            provider="qdrant",
            default_url="http://localhost:6333",
            default_collection="rag_chunks",
        ),
        "factory": "ragrails.models.vector_db.qdrant:QdrantStore",
    },
    "pinecone": {
        "info": VectorStoreInfo(
            provider="pinecone",
            default_url="",
            default_collection="rag-chunks",
        ),
        "factory": "ragrails.models.vector_db.pinecone:PineconeStore",
    },
    "weaviate": {
        "info": VectorStoreInfo(
            provider="weaviate",
            default_url="http://localhost:8080",
            default_collection="RagChunks",
        ),
        "factory": "ragrails.models.vector_db.weaviate:WeaviateStore",
    },
}


def list_vector_stores() -> list[VectorStoreInfo]:
    return [spec["info"] for spec in VECTOR_STORE_SPECS.values()]


def create_vector_store(
    provider: str = "qdrant",
    *,
    url: str | None = None,
    collection: str | None = None,
) -> VectorStore:
    if provider not in VECTOR_STORE_SPECS:
        available = ", ".join(sorted(VECTOR_STORE_SPECS))
        raise ValueError(f"Unknown vector DB provider '{provider}'. Available providers: {available}")

    spec = VECTOR_STORE_SPECS[provider]
    info = spec["info"]
    factory = _load_factory(spec["factory"])
    return factory(
        url=url or info.default_url,
        collection=collection or info.default_collection,
    )


def _load_factory(path: str):
    module_name, class_name = path.split(":", 1)
    module = import_module(module_name)
    return getattr(module, class_name)
