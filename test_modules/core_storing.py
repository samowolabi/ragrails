from __future__ import annotations

import json

from ragrails.models.vector_db.base import Point, SearchResult, VectorStore
from ragrails.core.stg_04_storing import store_embeddings
from ragrails.core.stg_04_storing.config import StoringConfig


class DemoStore(VectorStore):
    provider = "demo"
    collection = "demo_chunks"

    def ensure_collection(self, vector_size: int) -> None:
        print(f"ensure_collection(vector_size={vector_size})")

    def upsert(self, points: list[Point]) -> None:
        print(f"upsert(points={len(points)})")

    def delete(self, ids: list[str]) -> None:
        print(f"delete(ids={len(ids)})")

    def search(self, vector: list[float], top_k: int = 5) -> list[SearchResult]:
        return []


def main() -> None:
    result = store_embeddings(
        embedded_chunks=[
            {
                "id": "chunk-1",
                "source": "manual://demo",
                "text": "A short embedded chunk.",
                "embedding": [0.1, 0.2, 0.3],
                "metadata": {"title": "Demo"},
            }
        ],
        store=DemoStore(),
        config=StoringConfig(batch_size=64),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
