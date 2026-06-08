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
        with patch.object(RagRails, "chat", return_value=expected) as chat:
            result = run_chat(ChatRequest(query="auth", collection="docs", query_rewrite=QueryRewriteRequest(enabled=True, session_context="docs")))

        self.assertEqual(chat.call_args.args, ("auth",))
        self.assertTrue(chat.call_args.kwargs["query_rewrite"].enabled)
        self.assertEqual(chat.call_args.kwargs["query_rewrite"].session_context, "docs")
        self.assertEqual(result["answer"], "hello")


if __name__ == "__main__":
    unittest.main()
