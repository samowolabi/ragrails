import os
import re
from dataclasses import dataclass, field
from typing import Any

from dotenv import load_dotenv

from .base import Point, SearchResult, VectorStore


load_dotenv()


_INDEX_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


@dataclass
class PineconeStore(VectorStore):
    provider: str = "pinecone"
    url: str = ""
    collection: str = "rag-chunks"
    cloud: str = field(default_factory=lambda: os.environ.get("PINECONE_CLOUD", "aws"))
    region: str = field(default_factory=lambda: os.environ.get("PINECONE_REGION", "us-east-1"))
    metric: str = field(default_factory=lambda: os.environ.get("PINECONE_METRIC", "cosine"))
    namespace: str = field(default_factory=lambda: os.environ.get("PINECONE_NAMESPACE", ""))
    api_key: str | None = None
    _client: Any = field(init=False, repr=False, default=None)
    _index: Any = field(init=False, repr=False, default=None)

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from pinecone import Pinecone
            except ImportError as exc:
                raise RuntimeError(
                    "Pinecone support requires the 'pinecone' package. "
                    "Install project dependencies again with `uv sync`."
                ) from exc

            api_key = self.api_key or os.environ.get("PINECONE_API_KEY")
            if not api_key:
                raise RuntimeError("PINECONE_API_KEY is required when vector_db_provider='pinecone'")
            self._client = Pinecone(api_key=api_key)
        return self._client

    def _get_index(self) -> Any:
        if self._index is None:
            client = self._get_client()
            self._index = client.Index(host=self.url) if self.url else client.Index(self.collection)
        return self._index

    def _validate_index_name(self) -> None:
        if len(self.collection) > 45 or not _INDEX_NAME_PATTERN.match(self.collection):
            raise ValueError(
                "Pinecone index names must be 1-45 characters and contain only "
                "lowercase letters, digits, and hyphens. For example: 'rag-chunks'."
            )

    def ensure_collection(self, vector_size: int) -> None:
        """Create the Pinecone index if it does not exist.

        Ragrails passes externally generated vectors into Pinecone, so this uses
        a dense serverless index instead of Pinecone integrated embedding.

        Example:
            PineconeStore(collection="rag-chunks").ensure_collection(1024)
        """
        self._validate_index_name()
        client = self._get_client()
        if client.has_index(self.collection):
            print(f"Using existing Pinecone index: {self.collection}")
            return

        try:
            from pinecone import ServerlessSpec
        except ImportError as exc:
            raise RuntimeError(
                "Pinecone serverless index creation requires the 'pinecone' package. "
                "Install project dependencies again with `uv sync`."
            ) from exc

        client.create_index(
            name=self.collection,
            dimension=vector_size,
            metric=self.metric,
            spec=ServerlessSpec(cloud=self.cloud, region=self.region),
        )
        self._index = None
        print(f"Created Pinecone index: {self.collection}")

    def upsert(self, points: list[Point]) -> None:
        """Upsert a batch of dense vectors and payload metadata into Pinecone.

        Example:
            store.upsert([Point(id="abc-123", vector=[0.1, ...], payload={"text": "..."})])
        """
        if not points:
            return

        vectors = [
            {"id": p.id, "values": p.vector, "metadata": p.payload}
            for p in points
        ]
        kwargs = {"vectors": vectors}
        if self.namespace:
            kwargs["namespace"] = self.namespace
        self._get_index().upsert(**kwargs)

    def delete(self, ids: list[str]) -> None:
        """Delete vectors from the Pinecone index by exact vector IDs."""
        if not ids:
            return
        kwargs = {"ids": ids}
        if self.namespace:
            kwargs["namespace"] = self.namespace
        self._get_index().delete(**kwargs)

    def search(self, vector: list[float], top_k: int = 5) -> list[SearchResult]:
        """Return top-k nearest neighbours from a Pinecone dense-vector query.

        Example:
            results = store.search(query_vector, top_k=10)
        """
        kwargs = {
            "vector": vector,
            "top_k": top_k,
            "include_metadata": True,
        }
        if self.namespace:
            kwargs["namespace"] = self.namespace

        response = self._get_index().query(**kwargs)
        matches = self._read(response, "matches", [])
        return [self._to_result(match) for match in matches]

    def _to_result(self, match: Any) -> SearchResult:
        metadata = dict(self._read(match, "metadata", {}) or {})
        return SearchResult(
            id=str(self._read(match, "id", "")),
            score=float(self._read(match, "score", 0.0) or 0.0),
            text=metadata.pop("text", ""),
            metadata=metadata,
        )

    @staticmethod
    def _read(value: Any, key: str, default: Any = None) -> Any:
        if isinstance(value, dict):
            return value.get(key, default)
        return getattr(value, key, default)
