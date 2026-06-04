from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from click.testing import CliRunner

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
        fake_llm = object()
        fake_embedder = object()

        with self.runner.isolated_filesystem():
            with (
                patch.object(RagRails, "llm", return_value=fake_llm) as llm,
                patch.object(RagRails, "embedder", return_value=fake_embedder) as embedder,
                patch.object(RagRails, "chat", return_value=expected) as chat,
            ):
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
                    "gpt-4.1-mini",
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
        llm.assert_called_once_with(provider="openai", model="gpt-4.1-mini", max_tokens=512)
        embedder.assert_called_once_with(provider="voyage", model="voyage-3", input_type="query")
        call = chat.call_args.kwargs
        self.assertEqual(chat.call_args.args, ("How do payouts work?",))
        self.assertIs(call["llm"], fake_llm)
        self.assertIs(call["embedder"], fake_embedder)
        self.assertEqual(call["vector_db"], "qdrant")
        self.assertEqual(call["collection"], "rag_chunks")
        self.assertEqual(call["url"], "http://localhost:6333")
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
        fake_llm = object()
        fake_embedder = object()
        fake_reranker = object()

        with (
            patch.object(RagRails, "llm", return_value=fake_llm),
            patch.object(RagRails, "embedder", return_value=fake_embedder),
            patch.object(RagRails, "reranker", return_value=fake_reranker) as reranker,
            patch.object(RagRails, "chat", return_value=expected) as chat,
        ):
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
        reranker.assert_called_once_with(provider="voyage", model="rerank-2-lite")
        self.assertIs(chat.call_args.kwargs["reranker"], fake_reranker)
        self.assertTrue(chat.call_args.kwargs["retrieval_config"].use_rerank)
        self.assertEqual(chat.call_args.kwargs["retrieval_config"].rerank_top_k, 3)


if __name__ == "__main__":
    unittest.main()
