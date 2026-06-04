from __future__ import annotations

import json

from ragrails.models.embedder.base import EmbeddingModel
from ragrails.models.vector_db.base import Point, SearchResult, VectorStore
from ragrails.core.stg_05_retriever import retrieve_results


class DemoEmbedder(EmbeddingModel):
    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(texts[0]))]]

    @property
    def vector_size(self) -> int:
        return 1


class DemoStore(VectorStore):
    provider = "demo"
    collection = "demo_chunks"

    def ensure_collection(self, vector_size: int) -> None:
        return None

    def upsert(self, points: list[Point]) -> None:
        return None

    def delete(self, ids: list[str]) -> None:
        return None

    def search(self, vector: list[float], top_k: int = 5) -> list[SearchResult]:
        return [
            SearchResult(
                id="chunk-1",
                score=0.92,
                text="Use the query embedder for retrieval.",
                metadata={"source": "manual://retrieval"},
            )
        ][:top_k]


def main() -> None:
    result = retrieve_results(
        query="How does retrieval work?",
        model=DemoEmbedder(),
        store=DemoStore(),
        top_k=3,
    )
    printable = {
        **result,
        "outputs": [
            {
                "id": item.id,
                "score": item.score,
                "text": item.text,
                "metadata": item.metadata,
                "rerank_score": item.rerank_score,
            }
            for item in result["outputs"]
        ],
    }
    print(json.dumps(printable, indent=2))


if __name__ == "__main__":
    main()
