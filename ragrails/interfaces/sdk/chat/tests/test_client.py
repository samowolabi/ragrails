from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from ragrails.interfaces.sdk.chat.client import ChatMixin
from ragrails.interfaces.sdk.chat.config import (
    ChatRetrievalQualityConfig,
    HistoryCompactionConfig,
    IntentRoutingConfig,
    QueryRewriteConfig,
)
from ragrails.models.llm.base import LLMResponse


class SDK(ChatMixin):
    pass


class FakeEmbedder:
    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _ in texts]

    @property
    def vector_size(self) -> int:
        return 1


class FakeLLM:
    def __init__(self) -> None:
        self.summary_calls: list[dict] = []

    def complete(self, system: str, user: str, history=None, temperature=None) -> LLMResponse:
        self.summary_calls.append({"system": system, "user": user, "history": history, "temperature": temperature})
        return LLMResponse(
            text="User wants concise auth answers.",
            input_tokens=10,
            output_tokens=6,
            model="fake",
            provider="fake",
        )

    def stream(self, system: str, user: str, history=None, temperature=None):
        yield "Use "
        yield "bearer auth."


class FakeStore:
    collection = "docs"


def _chat_result(history: list[dict] | None = None) -> dict:
    return {
        "answer": "Use bearer auth.",
        "sources": [{"id": "C1"}],
        "history": history or [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ],
        "retrieval": {"retrieved": 1, "failed": 0, "outputs": [], "errors": []},
        "llm": {"provider": "fake", "model": "fake"},
        "errors": [],
        "retrieval_quality": {"status": "pass"},
        "answer_confidence": {"level": "medium", "reason": "test"},
        "intent": "rag",
    }


class SDKChatTests(unittest.TestCase):
    def test_chat_returns_result_without_compaction_under_limit(self) -> None:
        history = [{"role": "user", "content": "Question"}, {"role": "assistant", "content": "Answer"}]

        with (
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()) as create_store,
            patch("ragrails.core.stg_06_chat.run_chat", return_value=_chat_result(history)) as run_chat,
        ):
            result = SDK().chat(
                "How do I authenticate?",
                llm=FakeLLM(),
                embedder=FakeEmbedder(),
                vector_db="qdrant",
                collection="docs",
                url="http://localhost:6333",
                options={"api_key": "test"},
            )

        create_store.assert_called_once_with(
            provider="qdrant",
            url="http://localhost:6333",
            collection="docs",
            api_key="test",
        )
        self.assertEqual(run_chat.call_args.kwargs["query"], "How do I authenticate?")
        self.assertEqual(result.answer, "Use bearer auth.")
        self.assertEqual(result.history, history)
        self.assertEqual(result.answer_confidence, {"level": "medium", "reason": "test"})
        self.assertFalse(result.compacted)

    def test_chat_compacts_old_history_after_limit_and_keeps_recent_messages(self) -> None:
        llm = FakeLLM()
        full_history = [{"role": "user", "content": f"Message {index}"} for index in range(15)]

        with (
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()),
            patch("ragrails.core.stg_06_chat.run_chat", return_value=_chat_result(full_history)),
        ):
            result = SDK().chat(
                "Next question",
                llm=llm,
                embedder=FakeEmbedder(),
            )

        self.assertTrue(result.compacted)
        self.assertEqual(result.history[0], {
            "role": "system",
            "content": "Conversation summary: User wants concise auth answers.",
        })
        self.assertEqual(result.history[1:], full_history[-5:])
        self.assertIn("Message 0", llm.summary_calls[0]["user"])
        self.assertIn("Message 9", llm.summary_calls[0]["user"])
        self.assertNotIn("Message 10", llm.summary_calls[0]["user"])

    def test_chat_compaction_can_be_disabled(self) -> None:
        full_history = [{"role": "user", "content": f"Message {index}"} for index in range(17)]

        with (
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()),
            patch("ragrails.core.stg_06_chat.run_chat", return_value=_chat_result(full_history)),
        ):
            result = SDK().chat(
                "Next question",
                llm=FakeLLM(),
                embedder=FakeEmbedder(),
                history_compaction=HistoryCompactionConfig(enabled=False),
            )

        self.assertFalse(result.compacted)
        self.assertEqual(result.history, full_history)

    def test_chat_is_stateless_between_calls(self) -> None:
        sdk = SDK()

        with (
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()),
            patch("ragrails.core.stg_06_chat.run_chat", return_value=_chat_result([{"role": "user", "content": "First"}])),
        ):
            first = sdk.chat("First", llm=FakeLLM(), embedder=FakeEmbedder())

        with (
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()),
            patch("ragrails.core.stg_06_chat.run_chat", return_value=_chat_result()) as run_chat,
        ):
            sdk.chat("Second", llm=FakeLLM(), embedder=FakeEmbedder())

        self.assertEqual(first.history, [{"role": "user", "content": "First"}])
        self.assertEqual(run_chat.call_args.kwargs["history"], [])
        self.assertFalse(hasattr(sdk, "_sdk_chat_history"))

    def test_chat_uses_explicit_history(self) -> None:
        history = [{"role": "user", "content": "Previous question"}]

        with (
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()),
            patch("ragrails.core.stg_06_chat.run_chat", return_value=_chat_result()) as run_chat,
        ):
            SDK().chat("Second", llm=FakeLLM(), embedder=FakeEmbedder(), history=history)

        self.assertEqual(run_chat.call_args.kwargs["history"], history)

    def test_chat_forwards_query_rewrite_and_intent_flags(self) -> None:
        rewrite_llm = FakeLLM()
        with (
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()),
            patch("ragrails.core.stg_06_chat.run_chat", return_value=_chat_result()) as run_chat,
        ):
            SDK().chat(
                "How do I do it?",
                llm=FakeLLM(),
                embedder=FakeEmbedder(),
                persona="Product knowledge base",
                query_rewrite=QueryRewriteConfig(
                    enabled=True,
                    session_context="Auth flow",
                    llm=rewrite_llm,
                ),
                intent_routing=IntentRoutingConfig(enabled=False),
                retrieval_quality=ChatRetrievalQualityConfig(
                    min_retrieval_score=0.7,
                    min_rerank_score=0.8,
                    low_confidence_mode="ask_clarifying_question",
                    max_context_chunks=3,
                ),
            )

        call = run_chat.call_args.kwargs
        self.assertFalse(call["retrieval_config"].use_query_rewrite)
        self.assertTrue(call["query_rewrite"].enabled)
        self.assertIs(call["query_rewrite"].llm, rewrite_llm)
        self.assertEqual(call["query_rewrite"].context, "Product knowledge base")
        self.assertEqual(call["query_rewrite"].session_context, "Auth flow")
        self.assertFalse(call["chat_config"].use_intent_routing)
        self.assertEqual(call["chat_config"].retrieval_quality.min_retrieval_score, 0.7)
        self.assertEqual(call["chat_config"].retrieval_quality.min_rerank_score, 0.8)
        self.assertEqual(call["chat_config"].retrieval_quality.low_confidence_mode, "ask_clarifying_question")
        self.assertEqual(call["chat_config"].retrieval_quality.max_context_chunks, 3)

    def test_llm_creates_provider_object(self) -> None:
        fake_llm = FakeLLM()

        with patch("ragrails.models.llm.config.create_llm", return_value=fake_llm) as create_llm:
            result = SDK().llm(provider="openai", model="gpt-4o-mini", max_tokens=500)

        self.assertIs(result, fake_llm)
        config = create_llm.call_args.args[0]
        self.assertEqual(config.provider, "openai")
        self.assertEqual(config.model, "gpt-4o-mini")
        self.assertEqual(config.max_tokens, 500)

    def test_chat_wraps_missing_vector_store_dependency(self) -> None:
        with patch(
            "ragrails.models.vector_db.registry.create_vector_store",
            Mock(side_effect=ImportError("missing qdrant")),
        ):
            with self.assertRaisesRegex(RuntimeError, "Chat requires optional dependencies"):
                SDK().chat("Question", llm=FakeLLM(), embedder=FakeEmbedder())

    def test_chat_rejects_invalid_arguments(self) -> None:
        with self.assertRaisesRegex(ValueError, "query must be a non-empty string"):
            SDK().chat("", llm=FakeLLM(), embedder=FakeEmbedder())

        with self.assertRaisesRegex(TypeError, "llm must be an LLM object"):
            SDK().chat("Question", llm=object(), embedder=FakeEmbedder())

        with self.assertRaisesRegex(TypeError, "embedder must be an embedding model object"):
            SDK().chat("Question", llm=FakeLLM(), embedder="voyage")

        with self.assertRaisesRegex(ValueError, "history_compaction.history_limit must be greater than 0"):
            SDK().chat(
                "Question",
                llm=FakeLLM(),
                embedder=FakeEmbedder(),
                history_compaction=HistoryCompactionConfig(history_limit=0),
            )

        with self.assertRaisesRegex(ValueError, "history_compaction.keep_recent must be smaller"):
            SDK().chat(
                "Question",
                llm=FakeLLM(),
                embedder=FakeEmbedder(),
                history_compaction=HistoryCompactionConfig(history_limit=5, keep_recent=5),
            )

        with self.assertRaisesRegex(TypeError, "intent_routing must be an IntentRoutingConfig"):
            SDK().chat("Question", llm=FakeLLM(), embedder=FakeEmbedder(), intent_routing="yes")

        with self.assertRaisesRegex(TypeError, "retrieval_quality must be a ChatRetrievalQualityConfig"):
            SDK().chat("Question", llm=FakeLLM(), embedder=FakeEmbedder(), retrieval_quality="bad")

        with self.assertRaisesRegex(TypeError, "query_rewrite.llm must be an LLM object"):
            SDK().chat(
                "Question",
                llm=FakeLLM(),
                embedder=FakeEmbedder(),
                query_rewrite=QueryRewriteConfig(enabled=True, llm=object()),
            )

    def test_chat_stream_yields_progress_tokens_and_final_result(self) -> None:
        with (
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()),
            patch("ragrails.core.stg_05_retriever.run_retrieval", return_value={
                "query": "How do I authenticate?",
                "search_query": "How do I authenticate?",
                "retrieved": 0,
                "failed": 0,
                "outputs": [],
                "errors": [],
            }),
        ):
            events = list(SDK().chat_stream(
                "How do I authenticate?",
                llm=FakeLLM(),
                embedder=FakeEmbedder(),
                intent_routing=IntentRoutingConfig(enabled=False),
            ))

        self.assertEqual(events[0]["type"], "progress")
        self.assertIn("retrieval", [event["stage"] for event in events])
        self.assertEqual([event["data"]["text"] for event in events if event["type"] == "token"], ["Use ", "bearer auth."])
        self.assertEqual(events[-1]["type"], "final")
        self.assertEqual(events[-1]["data"]["answer"], "Use bearer auth.")


if __name__ == "__main__":
    unittest.main()
