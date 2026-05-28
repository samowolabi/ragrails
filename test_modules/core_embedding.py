from __future__ import annotations

import json

from ragrails.models.embedder.base import EmbeddingModel
from ragrails.core.stg_03_embedder.embedder import embed_chunks


class DemoEmbedder(EmbeddingModel):
    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), float(index)] for index, text in enumerate(texts)]

    @property
    def vector_size(self) -> int:
        return 2


def main() -> None:
    result = embed_chunks(
        chunks=[
            {
                "id": "chunk-1",
                "source": "manual://embedding",
                "text": "Visible chunk text",
                "embed_text": "Embedding text with title and heading",
                "metadata": {"id": "chunk-1", "title": "Embedding"},
            }
        ],
        model=DemoEmbedder(),
    )

    print(json.dumps({
        "embedded": result["embedded"],
        "failed": result["failed"],
        "first": result["outputs"][0] if result["outputs"] else None,
        "errors": result["errors"],
    }, indent=2))


if __name__ == "__main__":
    main()
