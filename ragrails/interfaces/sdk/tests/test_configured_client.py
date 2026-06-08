from __future__ import annotations

import unittest
from unittest.mock import patch

from ragrails.interfaces.sdk import RagRails


class FakeEmbedder:
    vector_size = 1

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _ in texts]


class FakeLLM:
    def complete(self, system: str, user: str, history=None, temperature=None):
        return None


class FakeReranker:
    def rerank(self, query: str, texts: list[str]) -> list[float]:
        return [1.0 for _ in texts]


class FakeStore:
    collection = "docs"


class ConfiguredClientTests(unittest.TestCase):
    def test_constructor_defaults_are_used_for_embedder_llm_and_reranker(self) -> None:
        rag = RagRails(
            embedding={"provider": "voyage", "model": "voyage-3-large"},
            llm={"provider": "openai", "model": "gpt-5.5", "max_tokens": 700},
            reranker={"enabled": True, "provider": "voyage", "model": "rerank-2"},
        )

        with (
            patch("ragrails.models.embedder.config.create_embedder", return_value=FakeEmbedder()) as create_embedder,
            patch("ragrails.models.llm.config.create_llm", return_value=FakeLLM()) as create_llm,
            patch("ragrails.models.reranker.config.create_reranker", return_value=FakeReranker()) as create_reranker,
        ):
            rag.embedder(input_type="query")
            rag.llm()
            first = rag.reranker()
            second = rag.reranker()

        embedder_config = create_embedder.call_args.args[0]
        self.assertEqual(embedder_config.provider, "voyage")
        self.assertEqual(embedder_config.model, "voyage-3-large")
        self.assertEqual(create_embedder.call_args.kwargs["input_type"], "query")

        llm_config = create_llm.call_args.args[0]
        self.assertEqual(llm_config.provider, "openai")
        self.assertEqual(llm_config.model, "gpt-5.5")
        self.assertEqual(llm_config.max_tokens, 700)

        reranker_config = create_reranker.call_args.args[0]
        self.assertEqual(reranker_config.provider, "voyage")
        self.assertEqual(reranker_config.model, "rerank-2")
        self.assertIs(first, second)

    def test_retrieve_uses_constructor_vector_store_and_query_embedder_defaults(self) -> None:
        rag = RagRails(
            collection="docs",
            vector_store={"provider": "qdrant", "url": "http://localhost:6333", "options": {"api_key": "default"}},
            embedding={"provider": "voyage", "model": "voyage-3"},
        )

        with (
            patch.object(rag, "embedder", return_value=FakeEmbedder()) as embedder,
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()) as create_store,
            patch(
                "ragrails.core.stg_05_retriever.retriever.run_retrieval",
                return_value={"query": "auth", "search_query": "auth", "retrieved": 0, "failed": 0, "outputs": [], "errors": []},
            ) as run_retrieval,
        ):
            rag.retrieve("auth")

        embedder.assert_called_once_with(input_type="query")
        create_store.assert_called_once_with(
            provider="qdrant",
            url="http://localhost:6333",
            collection="docs",
            api_key="default",
        )
        self.assertIs(run_retrieval.call_args.kwargs["model"], embedder.return_value)

    def test_per_call_vector_store_overrides_constructor_defaults(self) -> None:
        rag = RagRails(
            collection="docs",
            vector_store={"provider": "qdrant", "url": "http://localhost:6333"},
        )

        with (
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()) as create_store,
            patch(
                "ragrails.core.stg_04_storing.storing.store_embeddings",
                return_value={"stored": 1, "failed": 0, "outputs": [{"id": "chunk"}], "errors": []},
            ),
        ):
            rag.store(
                embedded_chunks=[{"id": "chunk", "text": "Text", "embedding": [1.0]}],
                collection="other_docs",
                options={"api_key": "override"},
            )

        create_store.assert_called_once_with(
            provider="qdrant",
            url="http://localhost:6333",
            collection="other_docs",
            api_key="override",
        )

    def test_chat_uses_configured_llm_embedder_vector_store_and_reranker(self) -> None:
        rag = RagRails(
            collection="docs",
            vector_store={"provider": "qdrant", "url": "http://localhost:6333"},
            embedding={"provider": "voyage", "model": "voyage-3"},
            llm={"provider": "openai", "model": "gpt-5.5"},
            reranker={"enabled": True, "provider": "voyage", "model": "rerank-2"},
        )
        llm = FakeLLM()
        embedder = FakeEmbedder()
        reranker = FakeReranker()

        with (
            patch.object(rag, "llm", return_value=llm) as create_llm,
            patch.object(rag, "embedder", return_value=embedder) as create_embedder,
            patch.object(rag, "reranker", return_value=reranker) as create_reranker,
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()),
            patch(
                "ragrails.core.stg_06_chat.run_chat",
                return_value={
                    "answer": "Answer",
                    "sources": [],
                    "history": [],
                    "retrieval": {},
                    "llm": {},
                    "errors": [],
                    "intent": "rag",
                },
            ) as run_chat,
        ):
            rag.chat("hello")

        create_llm.assert_called_once_with()
        create_embedder.assert_called_once_with(input_type="query")
        create_reranker.assert_called_once_with()
        self.assertIs(run_chat.call_args.kwargs["llm"], llm)
        self.assertIs(run_chat.call_args.kwargs["embedder"], embedder)
        self.assertIs(run_chat.call_args.kwargs["reranker"], reranker)

    def test_missing_configured_llm_for_chat_has_clear_error(self) -> None:
        with self.assertRaisesRegex(TypeError, "llm must be an LLM object"):
            RagRails().chat("hello", embedder=FakeEmbedder())

    def test_constructor_rejects_invalid_default_groups(self) -> None:
        with self.assertRaisesRegex(TypeError, "embedding must be a dictionary"):
            RagRails(embedding=["bad"])

        with self.assertRaisesRegex(TypeError, "collection must be a string"):
            RagRails(collection=123)


if __name__ == "__main__":
    unittest.main()
