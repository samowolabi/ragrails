from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from ragrails.interfaces.sdk.retrieval.client import RetrievalMixin
from ragrails.models.reranker.config import RerankerConfig
from ragrails.models.vector_db.base import SearchResult


class SDK(RetrievalMixin):
    pass


class FakeEmbedder:
    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _ in texts]

    @property
    def vector_size(self) -> int:
        return 1


class FakeReranker:
    def rerank(self, query: str, texts: list[str]) -> list[float]:
        return [1.0 for _ in texts]


class FakeLLM:
    def complete(self, system: str, user: str, history=None, temperature=None):
        return None


class FakeStore:
    collection = "docs"


class RetrievalSDKTests(unittest.TestCase):
    def test_reranker_creates_model_object(self) -> None:
        fake_reranker = FakeReranker()

        with patch("ragrails.models.reranker.config.create_reranker", return_value=fake_reranker) as create_reranker:
            result = SDK().reranker(
                provider="voyage",
                model="rerank-2-lite",
                options={"api_key": "test"},
            )

        self.assertIs(result, fake_reranker)
        config = create_reranker.call_args.args[0]
        self.assertIsInstance(config, RerankerConfig)
        self.assertEqual(config.provider, "voyage")
        self.assertEqual(config.model, "rerank-2-lite")
        self.assertEqual(config.options, {"api_key": "test"})

    def test_retrieve_returns_result_items(self) -> None:
        embedder = FakeEmbedder()
        reranker = FakeReranker()
        rewrite_llm = FakeLLM()
        output = SearchResult(
            id="chunk-1",
            score=0.91,
            text="Use bearer tokens.",
            metadata={"chunk_id": "chk-auth", "title": "Auth"},
            rerank_score=0.98,
        )
        stats = {
            "query": "how auth?",
            "search_query": "How do I authenticate?",
            "retrieved": 1,
            "failed": 0,
            "outputs": [output],
            "errors": [],
        }

        with (
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()) as create_store,
            patch("ragrails.core.stg_05_retriever.retriever.run_retrieval", return_value=stats) as run_retrieval,
        ):
            result = SDK().retrieve(
                "how auth?",
                embedder=embedder,
                vector_db="qdrant",
                collection="docs",
                url="http://localhost:6333",
                options={"api_key": "test"},
                top_k=20,
                use_query_rewrite=True,
                rewrite_llm=rewrite_llm,
                rewrite_context="Product docs",
                session_context="Auth question",
                use_rerank=True,
                reranker=reranker,
                rerank_top_k=5,
            )

        create_store.assert_called_once_with(
            provider="qdrant",
            url="http://localhost:6333",
            collection="docs",
            api_key="test",
        )
        call = run_retrieval.call_args.kwargs
        self.assertEqual(call["query"], "how auth?")
        self.assertIs(call["model"], embedder)
        self.assertIs(call["reranker"], reranker)
        self.assertIs(call["rewrite_llm"], rewrite_llm)
        self.assertEqual(call["config"].top_k, 20)
        self.assertTrue(call["config"].use_query_rewrite)
        self.assertTrue(call["config"].use_rerank)
        self.assertEqual(call["config"].rerank_top_k, 5)
        self.assertEqual(call["rewrite_context"], "Product docs")
        self.assertEqual(call["session_context"], "Auth question")

        self.assertEqual(result.query, "how auth?")
        self.assertEqual(result.search_query, "How do I authenticate?")
        self.assertEqual(result.retrieved, 1)
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.errors, [])
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].id, "chunk-1")
        self.assertEqual(result.items[0].chunk_id, "chk-auth")
        self.assertEqual(result.items[0].rerank_score, 0.98)

    def test_retrieve_preserves_core_errors(self) -> None:
        error = {"source": "query", "stage": "retrieve", "error": "failed"}
        stats = {
            "query": "auth",
            "search_query": "auth",
            "retrieved": 0,
            "failed": 1,
            "outputs": [],
            "errors": [error],
        }

        with (
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()),
            patch("ragrails.core.stg_05_retriever.retriever.run_retrieval", return_value=stats),
        ):
            result = SDK().retrieve("auth", embedder=FakeEmbedder())

        self.assertEqual(result.retrieved, 0)
        self.assertEqual(result.items, [])
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.errors, [error])

    def test_retrieve_wraps_missing_vector_store_dependency(self) -> None:
        with patch(
            "ragrails.models.vector_db.registry.create_vector_store",
            Mock(side_effect=ImportError("missing qdrant")),
        ):
            with self.assertRaisesRegex(RuntimeError, "Retrieval requires optional dependencies"):
                SDK().retrieve("auth", embedder=FakeEmbedder())

    def test_retrieve_rejects_invalid_query(self) -> None:
        with self.assertRaisesRegex(ValueError, "query must be a non-empty string"):
            SDK().retrieve("", embedder=FakeEmbedder())

    def test_retrieve_rejects_non_object_embedder(self) -> None:
        with self.assertRaisesRegex(TypeError, "embedding model object"):
            SDK().retrieve("auth", embedder="voyage")

    def test_retrieve_rejects_invalid_options(self) -> None:
        with self.assertRaisesRegex(TypeError, "options must be a dictionary"):
            SDK().retrieve("auth", embedder=FakeEmbedder(), options=["bad"])

    def test_retrieve_rejects_invalid_top_k(self) -> None:
        with self.assertRaisesRegex(ValueError, "top_k must be greater than 0"):
            SDK().retrieve("auth", embedder=FakeEmbedder(), top_k=0)

        with self.assertRaisesRegex(ValueError, "top_k must be greater than 0"):
            SDK().retrieve("auth", embedder=FakeEmbedder(), top_k=True)

    def test_retrieve_rejects_invalid_rerank_top_k(self) -> None:
        with self.assertRaisesRegex(ValueError, "rerank_top_k must be greater than 0"):
            SDK().retrieve("auth", embedder=FakeEmbedder(), rerank_top_k=0)

    def test_retrieve_rejects_query_rewrite_without_llm(self) -> None:
        with self.assertRaisesRegex(TypeError, "rewrite_llm must be an LLM object"):
            SDK().retrieve("auth", embedder=FakeEmbedder(), use_query_rewrite=True)

    def test_retrieve_rejects_rerank_without_reranker_object(self) -> None:
        with self.assertRaisesRegex(TypeError, "reranker must be a reranker object"):
            SDK().retrieve("auth", embedder=FakeEmbedder(), use_rerank=True)

    def test_reranker_rejects_required_strings(self) -> None:
        with self.assertRaisesRegex(ValueError, "provider is required"):
            SDK().reranker(provider="")

        with self.assertRaisesRegex(ValueError, "model is required"):
            SDK().reranker(model="")

    def test_reranker_rejects_invalid_options(self) -> None:
        with self.assertRaisesRegex(TypeError, "options must be a dictionary"):
            SDK().reranker(options=["bad"])


if __name__ == "__main__":
    unittest.main()
