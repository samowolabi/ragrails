from __future__ import annotations

import unittest

from ragrails.models.embedder.base import EmbeddingModel
from ragrails.models.llm.base import LLMProvider, LLMResponse, LLMToolResponse
from ragrails.models.reranker.base import Reranker
from ragrails.models.vector_db.base import Point, SearchResult, VectorStore
from ragrails.core.stg_05_retriever.config import RetrieverConfig
from ragrails.core.stg_05_retriever.retriever import (
    rerank,
    rerank_results,
    retrieve,
    retrieve_multi_results,
    retrieve_results,
    run_retrieval,
)


class FakeEmbedder(EmbeddingModel):
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(len(texts[0]))]]

    @property
    def vector_size(self) -> int:
        return 1


class FailingEmbedder(FakeEmbedder):
    def encode(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("embed unavailable")


class BadCountEmbedder(FakeEmbedder):
    def encode(self, texts: list[str]) -> list[list[float]]:
        return []


class FakeStore(VectorStore):
    provider = "fake"
    collection = "test"

    def __init__(self) -> None:
        self.searches: list[dict] = []

    def ensure_collection(self, vector_size: int) -> None:
        return None

    def upsert(self, points: list[Point]) -> None:
        return None

    def search(self, vector: list[float], top_k: int = 5) -> list[SearchResult]:
        self.searches.append({"vector": vector, "top_k": top_k})
        return [
            SearchResult(id="a", score=0.9, text="Alpha", metadata={"source": "manual://a"}),
            SearchResult(id="b", score=0.8, text="Bravo", metadata={"source": "manual://b"}),
        ][:top_k]


class FakeReranker(Reranker):
    def rerank(self, query: str, docs: list[str]) -> list[float]:
        return [0.1 if doc == "Alpha" else 0.9 for doc in docs]


class FailingReranker(FakeReranker):
    def rerank(self, query: str, docs: list[str]) -> list[float]:
        raise RuntimeError("rerank unavailable")


class BadCountReranker(FakeReranker):
    def rerank(self, query: str, docs: list[str]) -> list[float]:
        return [0.1]


class FakeLLM(LLMProvider):
    def __init__(self, text: str = "rewritten query") -> None:
        self.text = text
        self.calls: list[dict] = []

    def complete(self, system: str, user: str, history=None, temperature=None) -> LLMResponse:
        self.calls.append({"system": system, "user": user})
        return LLMResponse(
            text=self.text,
            input_tokens=1,
            output_tokens=1,
            model="fake",
            provider="fake",
        )

    def complete_with_tools(self, messages: list, system: str, tools: list[dict]) -> LLMToolResponse:
        return LLMToolResponse(text=self.text)


class FailingLLM(FakeLLM):
    def complete(self, system: str, user: str, history=None, temperature=None) -> LLMResponse:
        raise RuntimeError("rewrite unavailable")


class RetrieverCoreTests(unittest.TestCase):
    def test_run_retrieval_can_rewrite_query_from_core_config(self) -> None:
        model = FakeEmbedder()
        store = FakeStore()
        llm = FakeLLM("expanded auth query")

        result = run_retrieval(
            query="how do I do it?",
            model=model,
            store=store,
            rewrite_llm=llm,
            config=RetrieverConfig(top_k=2, use_query_rewrite=True),
            rewrite_context="Auth docs",
            session_context="User is asking about authentication.",
        )

        self.assertEqual(result["query"], "how do I do it?")
        self.assertEqual(result["search_query"], "expanded auth query")
        self.assertEqual(model.calls, [["expanded auth query"]])
        self.assertIn("Auth docs", llm.calls[0]["user"])
        self.assertIn("User is asking about authentication.", llm.calls[0]["user"])

    def test_run_retrieval_requires_rewrite_llm_when_rewrite_enabled(self) -> None:
        result = run_retrieval(
            query="hello",
            model=FakeEmbedder(),
            store=FakeStore(),
            config=RetrieverConfig(use_query_rewrite=True),
        )

        self.assertEqual(result, {
            "retrieved": 0,
            "failed": 1,
            "outputs": [],
            "errors": [
                {
                    "source": "hello",
                    "source_kind": "query",
                    "stage": "rewrite",
                    "error": "rewrite_llm is required when use_query_rewrite is True",
                    "isRetryable": False,
                    "attempts": 1,
                }
            ],
        })

    def test_run_retrieval_falls_back_to_original_query_when_rewrite_fails(self) -> None:
        model = FakeEmbedder()

        result = run_retrieval(
            query="hello",
            model=model,
            store=FakeStore(),
            rewrite_llm=FailingLLM(),
            config=RetrieverConfig(top_k=1, use_query_rewrite=True),
        )

        self.assertEqual(result["retrieved"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["search_query"], "hello")
        self.assertEqual(model.calls, [["hello"]])
        self.assertEqual(result["errors"], [
            {
                "source": "hello",
                "source_kind": "query",
                "stage": "rewrite",
                "error": "rewrite unavailable",
                "isRetryable": True,
                "attempts": 1,
            }
        ])

    def test_run_retrieval_can_skip_reranking_from_core_config(self) -> None:
        result = run_retrieval(
            query="hello",
            model=FakeEmbedder(),
            store=FakeStore(),
            reranker=FailingReranker(),
            config=RetrieverConfig(top_k=2, use_rerank=False),
        )

        self.assertEqual(result["retrieved"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertNotIn("reranked", result)
        self.assertEqual([item.id for item in result["outputs"]], ["a", "b"])
        self.assertEqual([item.rerank_score for item in result["outputs"]], [None, None])

    def test_run_retrieval_can_enable_reranking_from_core_config(self) -> None:
        result = run_retrieval(
            query="hello",
            model=FakeEmbedder(),
            store=FakeStore(),
            reranker=FakeReranker(),
            config=RetrieverConfig(top_k=2, use_rerank=True, rerank_top_k=1),
        )

        self.assertEqual(result["retrieved"], 2)
        self.assertEqual(result["reranked"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual([item.id for item in result["outputs"]], ["b"])
        self.assertEqual(result["outputs"][0].rerank_score, 0.9)

    def test_run_retrieval_requires_reranker_when_enabled(self) -> None:
        result = run_retrieval(
            query="hello",
            model=FakeEmbedder(),
            store=FakeStore(),
            config=RetrieverConfig(top_k=2, use_rerank=True),
        )

        self.assertEqual(result["retrieved"], 2)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"], [
            {
                "source": "hello",
                "source_kind": "query",
                "stage": "rerank",
                "error": "reranker is required when use_rerank is True",
                "isRetryable": False,
                "attempts": 1,
            }
        ])

    def test_run_retrieval_validates_config(self) -> None:
        result = run_retrieval(
            query="hello",
            model=FakeEmbedder(),
            store=FakeStore(),
            config=RetrieverConfig(top_k=0),
        )

        self.assertEqual(result, {
            "retrieved": 0,
            "failed": 1,
            "outputs": [],
            "errors": [
                {
                    "source": "",
                    "source_kind": "query",
                    "stage": "validate",
                    "error": "top_k must be greater than 0",
                    "isRetryable": False,
                    "attempts": 1,
                }
            ],
        })

    def test_retrieve_results_returns_structured_results(self) -> None:
        model = FakeEmbedder()
        store = FakeStore()

        result = retrieve_results(query="hello", model=model, store=store, top_k=2)

        self.assertEqual(result["retrieved"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["errors"], [])
        self.assertEqual([item.id for item in result["outputs"]], ["a", "b"])
        self.assertEqual(model.calls, [["hello"]])
        self.assertEqual(store.searches, [{"vector": [5.0], "top_k": 2}])

    def test_retrieve_compatibility_wrapper_returns_list(self) -> None:
        result = retrieve("hello", model=FakeEmbedder(), store=FakeStore(), top_k=1)

        self.assertEqual([item.id for item in result], ["a"])

    def test_retrieve_results_validates_query(self) -> None:
        result = retrieve_results(query="", model=FakeEmbedder(), store=FakeStore())

        self.assertEqual(result, {
            "retrieved": 0,
            "failed": 1,
            "outputs": [],
            "errors": [
                {
                    "source": "",
                    "source_kind": "query",
                    "stage": "validate",
                    "error": "query must be a non-empty string",
                    "isRetryable": False,
                    "attempts": 1,
                }
            ],
        })

    def test_retrieve_results_reports_model_failure(self) -> None:
        result = retrieve_results(query="hello", model=FailingEmbedder(), store=FakeStore())

        self.assertEqual(result["retrieved"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"], [
            {
                "source": "hello",
                "source_kind": "query",
                "stage": "retrieve",
                "error": "embed unavailable",
                "isRetryable": True,
                "attempts": 1,
            }
        ])

    def test_retrieve_results_reports_bad_vector_count(self) -> None:
        result = retrieve_results(query="hello", model=BadCountEmbedder(), store=FakeStore())

        self.assertEqual(result["retrieved"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"][0]["error"], "embedding model returned a different number of vectors than input queries")

    def test_retrieve_multi_results_dedupes_outputs(self) -> None:
        result = retrieve_multi_results(
            queries=["hello", "world"],
            model=FakeEmbedder(),
            store=FakeStore(),
            top_k_per_query=2,
        )

        self.assertEqual(result["retrieved"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertEqual([item.id for item in result["outputs"]], ["a", "b"])

    def test_rerank_results_returns_structured_sorted_results(self) -> None:
        results = [
            SearchResult(id="a", score=0.9, text="Alpha", metadata={}),
            SearchResult(id="b", score=0.8, text="Bravo", metadata={}),
        ]

        result = rerank_results(query="hello", results=results, model=FakeReranker(), top_k=2)

        self.assertEqual(result["reranked"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertEqual([item.id for item in result["outputs"]], ["b", "a"])
        self.assertEqual([item.rerank_score for item in result["outputs"]], [0.9, 0.1])

    def test_rerank_compatibility_wrapper_returns_list(self) -> None:
        results = [
            SearchResult(id="a", score=0.9, text="Alpha", metadata={}),
            SearchResult(id="b", score=0.8, text="Bravo", metadata={}),
        ]

        ranked = rerank("hello", results=results, model=FakeReranker(), top_k=1)

        self.assertEqual([item.id for item in ranked], ["b"])

    def test_rerank_results_reports_failure(self) -> None:
        results = [
            SearchResult(id="a", score=0.9, text="Alpha", metadata={}),
            SearchResult(id="b", score=0.8, text="Bravo", metadata={}),
        ]

        result = rerank_results(query="hello", results=results, model=FailingReranker())

        self.assertEqual(result["reranked"], 0)
        self.assertEqual(result["failed"], 2)
        self.assertEqual(result["errors"], [
            {
                "source": "hello",
                "source_kind": "query",
                "stage": "rerank",
                "error": "rerank unavailable",
                "isRetryable": True,
                "attempts": 1,
            }
        ])

    def test_rerank_results_reports_bad_score_count(self) -> None:
        results = [
            SearchResult(id="a", score=0.9, text="Alpha", metadata={}),
            SearchResult(id="b", score=0.8, text="Bravo", metadata={}),
        ]

        result = rerank_results(query="hello", results=results, model=BadCountReranker())

        self.assertEqual(result["reranked"], 0)
        self.assertEqual(result["failed"], 2)
        self.assertEqual(result["errors"][0]["error"], "reranker returned a different number of scores than input results")


if __name__ == "__main__":
    unittest.main()
