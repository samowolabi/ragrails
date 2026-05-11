from dataclasses import dataclass, field

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from .base import Point, SearchResult, VectorStore


@dataclass
class QdrantStore(VectorStore):
    provider: str = "qdrant"
    url: str = "http://localhost:6333"
    collection: str = "rag_chunks"
    _client: QdrantClient = field(init=False, repr=False, default=None)

    def _get_client(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(url=self.url)
        return self._client

    def ensure_collection(self, vector_size: int) -> None:
        """Create the Qdrant collection if it does not exist.

        Example:
            QdrantStore(collection="rag_chunks").ensure_collection(512)
            # → "Created collection: rag_chunks"
        """
        client = self._get_client()
        existing = {c.name for c in client.get_collections().collections}
        if self.collection not in existing:
            # COSINE distance is used because Voyage embeddings are optimized for
            # cosine similarity — it measures the angle between vectors, not magnitude,
            # which suits semantic similarity of text.
            client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            print(f"Created collection: {self.collection}")
        else:
            print(f"Using existing collection: {self.collection}")

    def upsert(self, points: list[Point]) -> None:
        """Upsert a batch of points into the Qdrant collection.

        Example:
            store.upsert([Point(id="abc-123", vector=[0.1, ...], payload={"text": "Bearer token auth"})])
        """
        client = self._get_client()
        qdrant_points = [
            PointStruct(id=p.id, vector=p.vector, payload=p.payload)
            for p in points
        ]
        client.upsert(collection_name=self.collection, points=qdrant_points)

    def search(self, vector: list[float], top_k: int = 5) -> list[SearchResult]:
        """Return top-k nearest neighbours for the given query vector.

        Example:
            results = store.search(query_vector, top_k=10)
            # → [SearchResult(id="abc-123", score=0.94, text="...", metadata={...}), ...]
        """
        # with_payload=True is required to get the stored text and metadata back alongside scores.
        response = self._get_client().query_points(
            collection_name=self.collection,
            query=vector,
            limit=top_k,
            with_payload=True,
        )
        return [
            SearchResult(
                id=str(hit.id),
                score=hit.score,
                text=hit.payload.get("text", ""),
                # text is separated out into its own field — exclude it from metadata
                # so it isn't duplicated in both places on the SearchResult
                metadata={k: v for k, v in hit.payload.items() if k != "text"},
            )
            for hit in response.points
        ]
