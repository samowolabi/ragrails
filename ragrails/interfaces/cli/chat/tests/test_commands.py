from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from click.testing import CliRunner

from ragrails.interfaces.cli.config import save_config
from ragrails.interfaces.cli.main import cli
from ragrails.interfaces.sdk import RagRails
from ragrails.types import ChatResult


class CliChatTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_chat_runs_sdk_one_shot_and_updates_history_file(self) -> None:
        expected = ChatResult(
            answer="Payouts run daily.",
            sources=[{"title": "Payments", "path": "/payments"}],
            history=[{"role": "user", "content": "How do payouts work?"}],
            retrieval={},
            llm={},
            errors=[],
            retrieval_quality={},
            answer_confidence={},
        )
        with self.runner.isolated_filesystem():
            with patch.object(RagRails, "chat", return_value=expected) as chat:
                result = self.runner.invoke(cli, [
                    "chat",
                    "How do payouts work?",
                    "--vector-db",
                    "qdrant",
                    "--collection",
                    "rag_chunks",
                    "--url",
                    "http://localhost:6333",
                    "--history-file",
                    "history/chat.json",
                    "--rewrite-query",
                    "--rewrite-session-context",
                    "Payment docs",
                    "--disable-intent-routing",
                    "--disable-history-compaction",
                    "--llm-provider",
                    "openai",
                    "--llm-model",
                    "gpt-4o-mini",
                    "--max-tokens",
                    "512",
                    "--embedder-provider",
                    "voyage",
                    "--embedder-model",
                    "voyage-3",
                ])

            with open("history/chat.json", encoding="utf-8") as file:
                saved_history = json.load(file)

        self.assertEqual(result.exit_code, 0, result.output)
        call = chat.call_args.kwargs
        self.assertEqual(chat.call_args.args, ("How do payouts work?",))
        self.assertTrue(call["query_rewrite"].enabled)
        self.assertEqual(call["query_rewrite"].session_context, "Payment docs")
        self.assertFalse(call["intent_routing"].enabled)
        self.assertFalse(call["history_compaction"].enabled)
        self.assertEqual(saved_history, expected.history)
        self.assertIn("Payouts run daily.", result.output)
        self.assertIn("Sources:", result.output)

    def test_chat_can_enable_rerank(self) -> None:
        expected = ChatResult(
            answer="Payouts run daily.",
            sources=[],
            history=[],
            retrieval={},
            llm={},
            errors=[],
            retrieval_quality={},
            answer_confidence={},
        )
        with self.runner.isolated_filesystem():
            with patch.object(RagRails, "chat", return_value=expected) as chat:
                result = self.runner.invoke(cli, [
                    "chat",
                    "How do payouts work?",
                    "--rerank",
                    "--reranker",
                    "voyage",
                    "--reranker-model",
                    "rerank-2-lite",
                    "--rerank-top-k",
                    "3",
                ])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertTrue(chat.call_args.kwargs["retrieval_config"].use_rerank)
        self.assertEqual(chat.call_args.kwargs["retrieval_config"].rerank_top_k, 3)

    def test_chat_uses_advanced_chat_defaults(self) -> None:
        expected = ChatResult(
            answer="Payouts run daily.",
            sources=[],
            history=[],
            retrieval={},
            llm={},
            errors=[],
            retrieval_quality={},
            answer_confidence={},
        )

        with self.runner.isolated_filesystem():
            save_config({
                "chat": {
                    "query_rewrite": True,
                    "intent_routing": False,
                    "history_compaction": False,
                },
                "retrieval": {"rerank_top_k": 4},
                "reranker": {"enabled": True, "provider": "voyage", "model": "rerank-2-lite"},
            })
            with patch.object(RagRails, "chat", return_value=expected) as chat:
                result = self.runner.invoke(cli, ["chat", "How do payouts work?"])

        self.assertEqual(result.exit_code, 0, result.output)
        call = chat.call_args.kwargs
        self.assertTrue(call["query_rewrite"].enabled)
        self.assertFalse(call["intent_routing"].enabled)
        self.assertFalse(call["history_compaction"].enabled)
        self.assertTrue(call["retrieval_config"].use_rerank)
        self.assertEqual(call["retrieval_config"].rerank_top_k, 4)


if __name__ == "__main__":
    unittest.main()
