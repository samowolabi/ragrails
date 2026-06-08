from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from ragrails.core.stg_05_retriever import RetrieverConfig
from ragrails.core.stg_06_chat import ChatConfig
from ragrails.interfaces.cli.chat.agentic import generate_agentic
from ragrails.interfaces.cli.chat.debug_trace import RagDebugTrace
from ragrails.interfaces.cli.chat.pipeline import _generate
from ragrails.interfaces.cli.chat.session import ChatSession
from ragrails.models.llm.base import LLMProvider, LLMResponse, LLMToolResponse, ToolCall
from ragrails.models.llm.config import LLMConfig
from ragrails.models.vector_db.base import SearchResult


class FakeToolLLM(LLMProvider):
    def __init__(self, responses: list[LLMToolResponse] | None = None) -> None:
        self.responses = responses or [LLMToolResponse(text="Final answer.")]
        self.tool_calls: list[dict] = []

    def complete(self, system: str, user: str, history=None, temperature=None) -> LLMResponse:
        return LLMResponse(
            text="Plain answer.",
            input_tokens=1,
            output_tokens=1,
            model="gpt-4o-mini",
            provider="openai",
        )

    def complete_with_tools(self, messages: list, system: str, tools: list[dict]) -> LLMToolResponse:
        self.tool_calls.append({"messages": list(messages), "system": system, "tools": tools})
        return self.responses.pop(0)


def _result() -> SearchResult:
    return SearchResult(
        id="chunk-1",
        score=0.9,
        rerank_score=0.9,
        text="Use Bearer token authentication.",
        metadata={"title": "Auth", "path": "https://docs.test/auth"},
    )


class AgenticChatTests(unittest.TestCase):
    def test_chat_config_exposes_repl_agentic_controls(self) -> None:
        config = ChatConfig()

        self.assertFalse(config.rewrite_query)
        self.assertTrue(config.use_tools)
        self.assertFalse(config.stream)
        self.assertEqual(config.history_limit, 15)
        self.assertEqual(config.min_retrieval_score, config.retrieval_quality.min_retrieval_score)
        self.assertEqual(config.min_rerank_score, config.retrieval_quality.min_rerank_score)

    def test_generate_agentic_executes_validated_tool_call(self) -> None:
        llm = FakeToolLLM([
            LLMToolResponse(
                text=None,
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        name="web_fetch",
                        arguments={"url": "https://example.com/docs"},
                    )
                ],
            ),
            LLMToolResponse(text="Use the fetched docs [C1]."),
        ])

        with patch("ragrails.interfaces.cli.chat.agentic.run_tool", return_value="Fetched docs") as run_tool:
            response = generate_agentic(
                "How do I authenticate?",
                [_result()],
                llm=llm,
                config=ChatConfig(),
                history=[],
            )

        run_tool.assert_called_once_with("web_fetch", {"url": "https://example.com/docs"})
        self.assertEqual(len(llm.tool_calls), 2)
        self.assertEqual(response.answer, "Use the fetched docs [C1].")
        self.assertEqual(response.history[-2]["content"], "How do I authenticate?")
        self.assertTrue(any(tool["name"] == "web_fetch" for tool in llm.tool_calls[0]["tools"]))

    def test_pipeline_uses_agentic_generation_when_tools_are_enabled(self) -> None:
        session = ChatSession(
            chat_config=ChatConfig(use_tools=True, stream=False),
            llm_config=LLMConfig(provider="openai", model="gpt-4o-mini", max_tokens=128),
            retriever_config=RetrieverConfig(),
            llm=FakeToolLLM(),
            embedder=Mock(),
            reranker=Mock(),
            vector_store=Mock(),
        )
        session.debug_trace = RagDebugTrace(original_query="How do I authenticate?")

        with patch("ragrails.interfaces.cli.chat.pipeline.generate_agentic") as agentic:
            agentic.return_value.answer = "Agentic answer."
            agentic.return_value.sources = []
            agentic.return_value.history = []
            agentic.return_value.rendered = False

            response = _generate("How do I authenticate?", [_result()], session)

        agentic.assert_called_once()
        self.assertEqual(response.answer, "Agentic answer.")
        self.assertEqual(session.debug_trace.generation_mode, "agentic")


if __name__ == "__main__":
    unittest.main()
