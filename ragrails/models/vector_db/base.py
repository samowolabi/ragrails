from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Point:
    id: str
    vector: list[float]
    payload: dict


@dataclass
class SearchResult:
    id: str
    score: float
    text: str
    metadata: dict = field(default_factory=dict)
    rerank_score: float | None = None


class VectorStore(ABC):
    provider: str
    collection: str

    @abstractmethod
    def ensure_collection(self, vector_size: int) -> None:
        """Create the collection if it does not exist.

        Example:
            store = create_vector_store(provider="qdrant", collection="rag_chunks")
            store.ensure_collection(vector_size=512)
        """
        ...

    @abstractmethod
    def upsert(self, points: list[Point]) -> None:
        """Upsert a batch of points into the collection.

        Example:
            store.upsert([Point(id="abc-123", vector=[0.1, 0.2, ...], payload={"text": "..."})])
        """
        ...

    @abstractmethod
    def search(self, vector: list[float], top_k: int = 5) -> list[SearchResult]:
        """Return top-k nearest neighbours for the given query vector.

        Example:
            results = store.search(query_vector, top_k=10)
            # → [SearchResult(id="abc-123", score=0.94, text="...", metadata={...}), ...]
        """
        ...
