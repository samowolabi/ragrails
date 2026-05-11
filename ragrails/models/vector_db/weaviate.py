import json
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv

from .base import Point, SearchResult, VectorStore


load_dotenv()


_COLLECTION_NAME_PATTERN = re.compile(r"^[A-Z][A-Za-z0-9]*$")


@dataclass
class WeaviateStore(VectorStore):
    provider: str = "weaviate"
    url: str = field(default_factory=lambda: os.environ.get("WEAVIATE_URL", "http://localhost:8080"))
    collection: str = "RagChunks"
    grpc_host: str = field(default_factory=lambda: os.environ.get("WEAVIATE_GRPC_HOST", ""))
    grpc_port: int = field(default_factory=lambda: int(os.environ.get("WEAVIATE_GRPC_PORT", "50051")))
    grpc_secure: bool | None = None
    api_key: str | None = None
    _client: Any = field(init=False, repr=False, default=None)

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import weaviate
                from weaviate.classes.init import Auth
            except ImportError as exc:
                raise RuntimeError(
                    "Weaviate support requires the 'weaviate-client' package. "
                    "Install project dependencies again with `uv sync`."
                ) from exc

            api_key = self.api_key or os.environ.get("WEAVIATE_API_KEY")
            auth = Auth.api_key(api_key) if api_key else None
            parsed = urlparse(self.url)
            if not parsed.scheme or not parsed.hostname:
                raise ValueError("Weaviate url must be an absolute URL, e.g. 'http://localhost:8080'")

            if api_key and "weaviate.cloud" in parsed.hostname:
                self._client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.url,
                    auth_credentials=auth,
                )
                return self._client

            http_secure = parsed.scheme == "https"
            self._client = weaviate.connect_to_custom(
                http_host=parsed.hostname,
                http_port=parsed.port or (443 if http_secure else 80),
                http_secure=http_secure,
                grpc_host=self.grpc_host or parsed.hostname,
                grpc_port=self.grpc_port,
                grpc_secure=self.grpc_secure if self.grpc_secure is not None else http_secure,
                auth_credentials=auth,
            )
        return self._client

    def _validate_collection_name(self) -> None:
        if not _COLLECTION_NAME_PATTERN.match(self.collection):
            raise ValueError(
                "Weaviate collection names must start with an uppercase letter and "
                "contain only letters and digits. For example: 'RagChunks'."
            )

    def ensure_collection(self, vector_size: int) -> None:
        """Create the Weaviate collection if it does not exist.

        Ragrails provides vectors itself, so the collection is configured with a
        self-provided vectorizer.

        Example:
            WeaviateStore(collection="RagChunks").ensure_collection(1024)
        """
        self._validate_collection_name()
        client = self._get_client()
        if client.collections.exists(self.collection):
            print(f"Using existing Weaviate collection: {self.collection}")
            return

        try:
            from weaviate.classes.config import Configure, DataType, Property
        except ImportError as exc:
            raise RuntimeError(
                "Weaviate collection creation requires the 'weaviate-client' package. "
                "Install project dependencies again with `uv sync`."
            ) from exc

        client.collections.create(
            name=self.collection,
            vector_config=Configure.Vectors.self_provided(),
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="point_id", data_type=DataType.TEXT),
                Property(name="source", data_type=DataType.TEXT),
                Property(name="path", data_type=DataType.TEXT),
                Property(name="title", data_type=DataType.TEXT),
                Property(name="description", data_type=DataType.TEXT),
                Property(name="original_type", data_type=DataType.TEXT),
                Property(name="heading", data_type=DataType.TEXT),
                Property(name="chunk_id", data_type=DataType.TEXT),
                Property(name="chunk_index", data_type=DataType.INT),
                Property(name="content_hash", data_type=DataType.TEXT),
                Property(name="table_id", data_type=DataType.TEXT),
                Property(name="columns", data_type=DataType.TEXT),
                Property(name="row_start", data_type=DataType.INT),
                Property(name="row_end", data_type=DataType.INT),
            ],
        )
        print(f"Created Weaviate collection: {self.collection}")

    def upsert(self, points: list[Point]) -> None:
        """Insert or replace a batch of dense vectors in Weaviate.

        Example:
            store.upsert([Point(id="abc-123", vector=[0.1, ...], payload={"text": "..."})])
        """
        if not points:
            return

        collection = self._get_client().collections.get(self.collection)
        for point in points:
            object_id = self._uuid_for(point.id)
            properties = self._properties_for(point)
            if collection.data.exists(object_id):
                collection.data.replace(uuid=object_id, properties=properties, vector=point.vector)
            else:
                collection.data.insert(uuid=object_id, properties=properties, vector=point.vector)

    def search(self, vector: list[float], top_k: int = 5) -> list[SearchResult]:
        """Return top-k nearest neighbours from a Weaviate near-vector query.

        Example:
            results = store.search(query_vector, top_k=10)
        """
        try:
            from weaviate.classes.query import MetadataQuery
        except ImportError as exc:
            raise RuntimeError(
                "Weaviate querying requires the 'weaviate-client' package. "
                "Install project dependencies again with `uv sync`."
            ) from exc

        response = self._get_client().collections.get(self.collection).query.near_vector(
            near_vector=vector,
            limit=top_k,
            return_metadata=MetadataQuery(distance=True),
        )
        return [self._to_result(obj) for obj in response.objects]

    def _to_result(self, obj: Any) -> SearchResult:
        properties = dict(getattr(obj, "properties", {}) or {})
        metadata = {k: v for k, v in properties.items() if k != "text"}
        point_id = metadata.pop("point_id", None)
        distance = getattr(getattr(obj, "metadata", None), "distance", None)
        score = max(0.0, 1.0 - float(distance)) if distance is not None else 0.0
        return SearchResult(
            id=str(point_id or getattr(obj, "uuid", "")),
            score=score,
            text=properties.get("text", ""),
            metadata=metadata,
        )

    def _properties_for(self, point: Point) -> dict:
        payload = dict(point.payload)
        payload["point_id"] = point.id
        return {
            key: self._property_value(value)
            for key, value in payload.items()
            if value is not None
        }

    @staticmethod
    def _uuid_for(point_id: str) -> uuid.UUID:
        return uuid.uuid5(uuid.NAMESPACE_URL, point_id)

    @staticmethod
    def _property_value(value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return json.dumps(value, sort_keys=True)
        return value
