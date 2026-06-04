from __future__ import annotations

import unittest

from ragrails.models.embedder.base import EmbeddingModel
from ragrails.models.llm.base import LLMProvider, LLMResponse, LLMToolResponse
from ragrails.models.reranker.base import Reranker
from ragrails.models.vector_db.base import Point, SearchResult, VectorStore
from ragrails.core.stg_05_retriever import RetrieverConfig
from ragrails.core.stg_06_chat import ChatConfig, QueryRewriteConfig, run_chat
from ragrails.core.stg_06_chat.context import build_context, extract_sources, select_context, validate_citations
from ragrails.core.stg_06_chat.quality import (
    ASK_CLARIFYING_QUESTION,
    REFUSE_GROUNDED_ANSWER,
    RETURN_NO_ANSWER,
    RetrievalQualityConfig,
)


class FakeEmbedder(EmbeddingModel):
    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(texts[0]))]]

    @property
    def vector_size(self) -> int:
        return 1


class FakeStore(VectorStore):
    provider = "fake"
    collection = "test"

    def ensure_collection(self, vector_size: int) -> None:
        return None

    def upsert(self, points: list[Point]) -> None:
        return None

    def delete(self, ids: list[str]) -> None:
        return None

    def search(self, vector: list[float], top_k: int = 5) -> list[SearchResult]:
        self.search_called = True
        return [
            SearchResult(
                id="a",
                score=0.8,
                text="Use Bearer token authentication.",
                metadata={"title": "Auth", "path": "https://docs.test/auth"},
            ),
            SearchResult(
                id="b",
                score=0.6,
                text="Use bank transfer for settlement.",
                metadata={"title": "Transfers", "path": "https://docs.test/transfers"},
            ),
        ][:top_k]


class EmptyStore(FakeStore):
    def search(self, vector: list[float], top_k: int = 5) -> list[SearchResult]:
        return []


class FakeReranker(Reranker):
    def rerank(self, query: str, texts: list[str]) -> list[float]:
        return [0.2, 0.9]


class FakeLLM(LLMProvider):
    def __init__(self, text: str = "Use Bearer auth [C1].") -> None:
        self.text = text
        self.calls: list[dict] = []

    def complete(self, system: str, user: str, history=None, temperature=None) -> LLMResponse:
        self.calls.append({"system": system, "user": user, "history": history or []})
        return LLMResponse(
            text=self.text,
            input_tokens=10,
            output_tokens=5,
            model="fake-llm",
            provider="fake",
        )

    def complete_with_tools(self, messages: list, system: str, tools: list[dict]) -> LLMToolResponse:
        return LLMToolResponse(text=self.text)


class RewriteLLM(FakeLLM):
    def __init__(self, text: str = "expanded auth query") -> None:
        super().__init__(text)


class FailingLLM(FakeLLM):
    def complete(self, system: str, user: str, history=None, temperature=None) -> LLMResponse:
        raise RuntimeError("llm unavailable")


class FailingRewriteLLM(FakeLLM):
    def complete(self, system: str, user: str, history=None, temperature=None) -> LLMResponse:
        raise RuntimeError("rewrite unavailable")


class ChatCoreTests(unittest.TestCase):
    def test_run_chat_bypasses_retrieval_for_small_talk(self) -> None:
        llm = FakeLLM("You are welcome.")
        store = FakeStore()

        result = run_chat(
            query="thank you",
            llm=llm,
            embedder=FakeEmbedder(),
            store=store,
        )

        self.assertEqual(result["answer"], "You are welcome.")
        self.assertEqual(result["intent"], "thanks")
        self.assertEqual(result["retrieval"], {"retrieved": 0, "failed": 0, "outputs": [], "errors": []})
        self.assertFalse(hasattr(store, "search_called"))
        self.assertEqual(result["history"][-2:], [
            {"role": "user", "content": "thank you"},
            {"role": "assistant", "content": "You are welcome."},
        ])

    def test_run_chat_can_disable_intent_routing(self) -> None:
        store = FakeStore()

        result = run_chat(
            query="hello",
            llm=FakeLLM(),
            embedder=FakeEmbedder(),
            store=store,
            chat_config=ChatConfig(use_intent_routing=False),
        )

        self.assertEqual(result["intent"], "rag")
        self.assertTrue(store.search_called)

    def test_run_chat_without_rerank(self) -> None:
        llm = FakeLLM()

        result = run_chat(
            query="How do I authenticate?",
            llm=llm,
            embedder=FakeEmbedder(),
            store=FakeStore(),
            chat_config=ChatConfig(persona="You answer docs questions."),
            retrieval_config=RetrieverConfig(top_k=2, use_rerank=False),
        )

        self.assertEqual(result["answer"], "Use Bearer auth [C1].")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["retrieval"]["retrieved"], 2)
        self.assertEqual([source["id"] for source in result["sources"]], ["C1", "C2"])
        self.assertEqual(result["answer_confidence"]["level"], "high")
        self.assertIn("Context:", llm.calls[0]["user"])
        self.assertIn("[C1] Auth", llm.calls[0]["user"])
        self.assertEqual(result["history"][-2:], [
            {"role": "user", "content": "How do I authenticate?"},
            {"role": "assistant", "content": "Use Bearer auth [C1]."},
        ])

    def test_run_chat_with_rerank(self) -> None:
        result = run_chat(
            query="How do I settle?",
            llm=FakeLLM("Use transfers [C1]."),
            embedder=FakeEmbedder(),
            store=FakeStore(),
            reranker=FakeReranker(),
            retrieval_config=RetrieverConfig(top_k=2, use_rerank=True, rerank_top_k=1),
        )

        self.assertEqual(result["retrieval"]["retrieved"], 2)
        self.assertEqual(result["retrieval"]["reranked"], 1)
        self.assertEqual(result["sources"][0]["title"], "Transfers")
        self.assertEqual(result["answer"], "Use transfers [C1].")

    def test_run_chat_with_no_context_still_calls_llm(self) -> None:
        llm = FakeLLM("I need more detail.")

        result = run_chat(
            query="Hello",
            llm=llm,
            embedder=FakeEmbedder(),
            store=EmptyStore(),
        )

        self.assertEqual(result["answer"], "I need more detail.")
        self.assertEqual(result["sources"], [])
        self.assertEqual(llm.calls[0]["user"], "Hello")

    def test_run_chat_uses_separate_rewrite_llm_when_provided(self) -> None:
        answer_llm = FakeLLM("Use Bearer auth [C1].")
        rewrite_llm = RewriteLLM("expanded auth query")

        result = run_chat(
            query="How do I do it?",
            llm=answer_llm,
            embedder=FakeEmbedder(),
            store=FakeStore(),
            chat_config=ChatConfig(persona="Product docs"),
            retrieval_config=RetrieverConfig(top_k=1),
            query_rewrite=QueryRewriteConfig(
                enabled=True,
                llm=rewrite_llm,
                session_context="User is asking about authentication.",
            ),
        )

        self.assertEqual(result["errors"], [])
        self.assertEqual(result["retrieval"]["query"], "How do I do it?")
        self.assertEqual(result["retrieval"]["search_query"], "expanded auth query")
        self.assertIn("Product docs", rewrite_llm.calls[0]["user"])
        self.assertIn("User is asking about authentication.", rewrite_llm.calls[0]["user"])
        self.assertIn("Context:", answer_llm.calls[0]["user"])
        self.assertEqual(result["history"][-2], {"role": "user", "content": "How do I do it?"})

    def test_run_chat_falls_back_to_chat_llm_for_query_rewrite(self) -> None:
        llm = FakeLLM("expanded auth query")

        result = run_chat(
            query="How do I do it?",
            llm=llm,
            embedder=FakeEmbedder(),
            store=FakeStore(),
            retrieval_config=RetrieverConfig(top_k=1),
            query_rewrite=QueryRewriteConfig(enabled=True),
        )

        self.assertEqual(result["errors"], [])
        self.assertEqual(result["retrieval"]["search_query"], "expanded auth query")
        self.assertEqual(len(llm.calls), 2)
        self.assertIn("Current query: How do I do it?", llm.calls[0]["user"])
        self.assertIn("Context:", llm.calls[1]["user"])

    def test_run_chat_skips_query_rewrite_when_disabled(self) -> None:
        answer_llm = FakeLLM("Use Bearer auth [C1].")
        rewrite_llm = RewriteLLM("expanded auth query")

        result = run_chat(
            query="How do I do it?",
            llm=answer_llm,
            embedder=FakeEmbedder(),
            store=FakeStore(),
            retrieval_config=RetrieverConfig(top_k=1),
            query_rewrite=QueryRewriteConfig(enabled=False, llm=rewrite_llm),
        )

        self.assertEqual(result["errors"], [])
        self.assertEqual(result["retrieval"]["query"], "How do I do it?")
        self.assertEqual(result["retrieval"]["search_query"], "How do I do it?")
        self.assertEqual(rewrite_llm.calls, [])
        self.assertEqual(len(answer_llm.calls), 1)
        self.assertIn("Context:", answer_llm.calls[0]["user"])

    def test_run_chat_returns_rewrite_errors_and_search_query(self) -> None:
        result = run_chat(
            query="How do I do it?",
            llm=FakeLLM(),
            embedder=FakeEmbedder(),
            store=FakeStore(),
            retrieval_config=RetrieverConfig(top_k=1),
            query_rewrite=QueryRewriteConfig(enabled=True, llm=FailingRewriteLLM()),
        )

        self.assertEqual(result["answer"], "")
        self.assertEqual(result["errors"][0]["stage"], "rewrite")
        self.assertEqual(result["errors"][0]["error"], "rewrite unavailable")
        self.assertEqual(result["retrieval"]["query"], "How do I do it?")
        self.assertEqual(result["retrieval"]["search_query"], "How do I do it?")

    def test_run_chat_limits_context_from_config(self) -> None:
        llm = FakeLLM("Use auth [C1].")

        result = run_chat(
            query="How do I authenticate?",
            llm=llm,
            embedder=FakeEmbedder(),
            store=FakeStore(),
            chat_config=ChatConfig(
                retrieval_quality=RetrievalQualityConfig(
                    min_retrieval_score=0.7,
                    max_context_chunks=1,
                )
            ),
            retrieval_config=RetrieverConfig(top_k=2),
        )

        self.assertEqual([source["id"] for source in result["sources"]], ["C1"])
        self.assertIn("[C1] Auth", llm.calls[0]["user"])
        self.assertNotIn("[C2] Transfers", llm.calls[0]["user"])

    def test_run_chat_answers_cautiously_when_retrieval_quality_is_low(self) -> None:
        llm = FakeLLM("I am not confident enough to answer.")

        result = run_chat(
            query="How do I authenticate?",
            llm=llm,
            embedder=FakeEmbedder(),
            store=FakeStore(),
            chat_config=ChatConfig(
                retrieval_quality=RetrievalQualityConfig(min_retrieval_score=0.95)
            ),
        )

        self.assertEqual(result["answer"], "I am not confident enough to answer.")
        self.assertEqual(result["sources"], [])
        self.assertEqual(result["retrieval_quality"]["status"], "low_confidence")
        self.assertEqual(result["retrieval_quality"]["passed_chunks"], 0)
        self.assertEqual(result["answer_confidence"]["level"], "low")
        self.assertIn("not confident enough", llm.calls[0]["user"])

    def test_run_chat_can_ask_clarifying_question_for_low_quality_retrieval(self) -> None:
        llm = FakeLLM("Can you clarify which auth flow you mean?")

        result = run_chat(
            query="How do I authenticate?",
            llm=llm,
            embedder=FakeEmbedder(),
            store=FakeStore(),
            chat_config=ChatConfig(
                retrieval_quality=RetrievalQualityConfig(
                    min_retrieval_score=0.95,
                    low_confidence_mode=ASK_CLARIFYING_QUESTION,
                )
            ),
        )

        self.assertEqual(result["answer"], "Can you clarify which auth flow you mean?")
        self.assertEqual(result["retrieval_quality"]["mode"], ASK_CLARIFYING_QUESTION)
        self.assertIn("Ask one concise clarifying question", llm.calls[0]["user"])

    def test_run_chat_can_return_no_answer_for_low_quality_retrieval(self) -> None:
        result = run_chat(
            query="How do I authenticate?",
            llm=FakeLLM(),
            embedder=FakeEmbedder(),
            store=FakeStore(),
            chat_config=ChatConfig(
                retrieval_quality=RetrievalQualityConfig(
                    min_retrieval_score=0.95,
                    low_confidence_mode=RETURN_NO_ANSWER,
                )
            ),
        )

        self.assertEqual(result["answer"], "")
        self.assertEqual(result["history"], [])
        self.assertEqual(result["errors"][0]["stage"], "quality")
        self.assertEqual(result["retrieval_quality"]["mode"], RETURN_NO_ANSWER)
        self.assertEqual(result["answer_confidence"]["level"], "none")

    def test_run_chat_can_refuse_grounded_answer_naturally_for_low_quality_retrieval(self) -> None:
        llm = FakeLLM("I could not find enough relevant context to answer that reliably.")

        result = run_chat(
            query="How do I authenticate?",
            llm=llm,
            embedder=FakeEmbedder(),
            store=FakeStore(),
            chat_config=ChatConfig(
                retrieval_quality=RetrievalQualityConfig(
                    min_retrieval_score=0.95,
                    low_confidence_mode=REFUSE_GROUNDED_ANSWER,
                )
            ),
        )

        self.assertEqual(result["answer"], "I could not find enough relevant context to answer that reliably.")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["retrieval_quality"]["mode"], REFUSE_GROUNDED_ANSWER)
        self.assertIn("not enough relevant context", llm.calls[0]["user"])

    def test_run_chat_returns_retrieval_errors(self) -> None:
        result = run_chat(
            query="How do I authenticate?",
            llm=FakeLLM(),
            embedder=FakeEmbedder(),
            store=FakeStore(),
            retrieval_config=RetrieverConfig(top_k=0),
        )

        self.assertEqual(result["answer"], "")
        self.assertEqual(result["errors"][0]["stage"], "validate")
        self.assertEqual(result["errors"][0]["error"], "top_k must be greater than 0")

    def test_run_chat_returns_llm_errors(self) -> None:
        result = run_chat(
            query="How do I authenticate?",
            llm=FailingLLM(),
            embedder=FakeEmbedder(),
            store=FakeStore(),
        )

        self.assertEqual(result["answer"], "")
        self.assertEqual(result["errors"], [
            {
                "source": "",
                "source_kind": "chat",
                "stage": "generate",
                "error": "llm unavailable",
                "isRetryable": True,
                "attempts": 1,
            }
        ])

    def test_context_helpers(self) -> None:
        results = [
            SearchResult(id="a", score=0.8, text="Alpha", metadata={"title": "A", "heading": {"h1": "Intro"}}),
            SearchResult(id="b", score=0.2, text="Bravo", metadata={"title": "B"}),
        ]

        selected = select_context(results, min_score=0.5)
        context = build_context(selected)
        sources = extract_sources(selected)

        self.assertEqual([item.id for item in selected], ["a"])
        self.assertIn("[C1] A - Intro", context)
        self.assertEqual(sources[0]["chunk_id"], "a")
        self.assertEqual(validate_citations("See [C1] and [C9].", sources), "See [C1] and [invalid:C9].")

    def test_run_chat_validates_query(self) -> None:
        result = run_chat(query="", llm=FakeLLM(), embedder=FakeEmbedder(), store=FakeStore())

        self.assertEqual(result["answer"], "")
        self.assertEqual(result["errors"][0]["error"], "query must be a non-empty string")

    def test_run_chat_validates_history_is_a_list(self) -> None:
        result = run_chat(
            query="How do I authenticate?",
            llm=FakeLLM(),
            embedder=FakeEmbedder(),
            store=FakeStore(),
            history="bad",
        )

        self.assertEqual(result["answer"], "")
        self.assertEqual(result["history"], [])
        self.assertEqual(result["errors"][0]["stage"], "validate")
        self.assertEqual(result["errors"][0]["error"], "history must be a list of messages")

    def test_run_chat_validates_history_message_shape(self) -> None:
        cases = [
            ([{"role": "user", "content": "Hi"}, "bad"], "history[1] must be a message dictionary"),
            ([{"role": "tool", "content": "Hi"}], "history[0].role must be one of: assistant, system, user"),
            ([{"role": "user", "content": None}], "history[0].content must be a string"),
        ]

        for history, error in cases:
            with self.subTest(error=error):
                result = run_chat(
                    query="How do I authenticate?",
                    llm=FakeLLM(),
                    embedder=FakeEmbedder(),
                    store=FakeStore(),
                    history=history,
                )

                self.assertEqual(result["answer"], "")
                self.assertEqual(result["errors"][0]["stage"], "validate")
                self.assertEqual(result["errors"][0]["error"], error)

    def test_run_chat_accepts_system_history_messages(self) -> None:
        llm = FakeLLM("Use Bearer auth [C1].")
        history = [{"role": "system", "content": "Conversation summary: user asks about auth."}]

        result = run_chat(
            query="How do I authenticate?",
            llm=llm,
            embedder=FakeEmbedder(),
            store=FakeStore(),
            history=history,
        )

        self.assertEqual(result["errors"], [])
        self.assertEqual(llm.calls[0]["history"], history)
        self.assertEqual(result["history"][0], history[0])


if __name__ == "__main__":
    unittest.main()
