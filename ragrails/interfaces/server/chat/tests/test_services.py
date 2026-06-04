from __future__ import annotations

import unittest
from unittest.mock import patch

from ragrails.interfaces.server.chat.schemas import ChatRequest, QueryRewriteRequest
from ragrails.interfaces.server.chat.services import run_chat
from ragrails.interfaces.sdk import RagRails
from ragrails.types import ChatResult


class ServerChatServiceTests(unittest.TestCase):
    def test_chat_creates_models_and_calls_sdk(self) -> None:
        expected = ChatResult(
            answer="hello",
            sources=[],
            history=[],
            retrieval={},
            llm={},
            errors=[],
            retrieval_quality={},
            answer_confidence={},
        )
        fake_llm = object()
        fake_embedder = object()

        with (
            patch.object(RagRails, "llm", return_value=fake_llm) as llm,
            patch.object(RagRails, "embedder", return_value=fake_embedder) as embedder,
            patch.object(RagRails, "chat", return_value=expected) as chat,
        ):
            result = run_chat(ChatRequest(query="auth", collection="docs", query_rewrite=QueryRewriteRequest(enabled=True, session_context="docs")))

        llm.assert_called_once_with(provider="openai", model="gpt-4.1-mini", max_tokens=1024)
        embedder.assert_called_once_with(provider="voyage", model="voyage-3", input_type="query", options=None)
        self.assertEqual(chat.call_args.args, ("auth",))
        self.assertTrue(chat.call_args.kwargs["query_rewrite"].enabled)
        self.assertEqual(chat.call_args.kwargs["query_rewrite"].session_context, "docs")
        self.assertEqual(result["answer"], "hello")


if __name__ == "__main__":
    unittest.main()
