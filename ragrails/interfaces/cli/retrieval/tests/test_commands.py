from __future__ import annotations

import unittest
from unittest.mock import patch

from click.testing import CliRunner

from ragrails.interfaces.cli.config import save_config
from ragrails.interfaces.cli.main import cli
from ragrails.interfaces.sdk import RagRails
from ragrails.types import RetrievedChunk, RetrieveResult


class CliRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_retrieve_passes_query_and_rerank_options_to_sdk(self) -> None:
        expected = RetrieveResult(
            query="How do payouts work?",
            search_query="How do payouts work?",
            retrieved=1,
            items=[
                RetrievedChunk(
                    id="chunk-1",
                    chunk_id="chk-payments",
                    score=0.91,
                    text="Payouts are processed daily.",
                    metadata={"title": "Payments", "path": "/payments"},
                    rerank_score=0.97,
                )
            ],
            failed=0,
            errors=[],
        )
        with patch.object(RagRails, "retrieve", return_value=expected) as retrieve:
            result = self.runner.invoke(cli, [
                "retrieve",
                "How do payouts work?",
                "--vector-db",
                "qdrant",
                "--collection",
                "rag_chunks",
                "--url",
                "http://localhost:6333",
                "--top-k",
                "20",
                "--provider",
                "voyage",
                "--model",
                "voyage-3",
                "--rerank",
                "--reranker",
                "voyage",
                "--reranker-model",
                "rerank-2-lite",
                "--rerank-top-k",
                "5",
            ])

        self.assertEqual(result.exit_code, 0, result.output)
        retrieve.assert_called_once_with(
            "How do payouts work?",
            top_k=20,
            use_rerank=True,
            rerank_top_k=5,
        )
        self.assertIn("Results: 1", result.output)
        self.assertIn("chunk_id=chk-payments", result.output)
        self.assertIn("rerank=0.9700", result.output)

    def test_retrieve_uses_project_config_defaults(self) -> None:
        expected = RetrieveResult(query="auth", search_query="auth", retrieved=0, items=[], failed=0, errors=[])
        captured = {}

        class FakeRagRails:
            def __init__(self, **kwargs):
                captured["init"] = kwargs

            def retrieve(self, *args, **kwargs):
                captured["retrieve"] = {"args": args, "kwargs": kwargs}
                return expected

        with self.runner.isolated_filesystem():
            save_config({
                "vector_store": {"provider": "qdrant", "collection": "docs", "url": "http://localhost:6333"},
                "embedding": {"provider": "voyage", "model": "voyage-3-large"},
                "reranker": {"enabled": True, "provider": "voyage", "model": "rerank-2-lite"},
                "retrieval": {"top_k": 7, "rerank_top_k": 4},
            })
            with patch("ragrails.interfaces.cli.retrieval.commands.RagRails", FakeRagRails):
                result = self.runner.invoke(cli, ["retrieve", "auth"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(captured["init"]["collection"], "docs")
        self.assertEqual(captured["init"]["vector_store"], {"provider": "qdrant", "url": "http://localhost:6333"})
        self.assertEqual(captured["init"]["embedding"], {"provider": "voyage", "model": "voyage-3-large"})
        self.assertEqual(captured["init"]["reranker"], {"enabled": True, "provider": "voyage", "model": "rerank-2-lite"})
        self.assertEqual(captured["retrieve"]["kwargs"]["top_k"], 7)
        self.assertTrue(captured["retrieve"]["kwargs"]["use_rerank"])
        self.assertEqual(captured["retrieve"]["kwargs"]["rerank_top_k"], 4)

    def test_retrieve_flags_override_project_config(self) -> None:
        expected = RetrieveResult(query="auth", search_query="auth", retrieved=0, items=[], failed=0, errors=[])
        captured = {}

        class FakeRagRails:
            def __init__(self, **kwargs):
                captured["init"] = kwargs

            def retrieve(self, *args, **kwargs):
                captured["retrieve"] = {"args": args, "kwargs": kwargs}
                return expected

        with self.runner.isolated_filesystem():
            save_config({
                "vector_store": {"provider": "qdrant", "collection": "docs"},
                "embedding": {"provider": "voyage", "model": "voyage-3-large"},
                "reranker": {"enabled": True, "provider": "voyage", "model": "rerank-2-lite"},
            })
            with patch("ragrails.interfaces.cli.retrieval.commands.RagRails", FakeRagRails):
                result = self.runner.invoke(cli, [
                    "retrieve",
                    "auth",
                    "--collection",
                    "other_docs",
                    "--model",
                    "voyage-3",
                    "--no-rerank",
                ])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(captured["init"]["collection"], "other_docs")
        self.assertEqual(captured["init"]["embedding"], {"provider": "voyage", "model": "voyage-3"})
        self.assertEqual(captured["init"]["reranker"]["enabled"], False)
        self.assertFalse(captured["retrieve"]["kwargs"]["use_rerank"])


if __name__ == "__main__":
    unittest.main()
