from __future__ import annotations

import json

from ragrails.models.embedder.base import EmbeddingModel
from ragrails.models.llm.base import LLMProvider, LLMResponse, LLMToolResponse
from ragrails.models.vector_db.base import Point, SearchResult, VectorStore
from ragrails.core.stg_05_retriever import RetrieverConfig
from ragrails.core.stg_06_chat import ChatConfig, run_chat


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
                score=0.91,
                text="Authentication uses an Authorization header with a Bearer token.",
                metadata={"title": "Authentication", "path": "manual://auth"},
            )
        ][:top_k]


class DemoLLM(LLMProvider):
    def complete(self, system: str, user: str, history=None, temperature=None) -> LLMResponse:
        return LLMResponse(
            text="Use the Authorization header with a Bearer token [C1].",
            input_tokens=10,
            output_tokens=8,
            model="demo",
            provider="demo",
        )

    def complete_with_tools(self, messages: list, system: str, tools: list[dict]) -> LLMToolResponse:
        return LLMToolResponse(text="")


def main() -> None:
    result = run_chat(
        query="How do I authenticate?",
        llm=DemoLLM(),
        embedder=DemoEmbedder(),
        store=DemoStore(),
        chat_config=ChatConfig(persona="You answer product documentation questions."),
        retrieval_config=RetrieverConfig(top_k=3, use_rerank=False),
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
