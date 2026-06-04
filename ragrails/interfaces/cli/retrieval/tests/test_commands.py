from __future__ import annotations

import unittest
from unittest.mock import patch

from click.testing import CliRunner

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
                    score=0.91,
                    text="Payouts are processed daily.",
                    metadata={"title": "Payments", "path": "/payments"},
                    rerank_score=0.97,
                )
            ],
            failed=0,
            errors=[],
        )
        fake_embedder = object()
        fake_reranker = object()

        with (
            patch.object(RagRails, "embedder", return_value=fake_embedder) as embedder,
            patch.object(RagRails, "reranker", return_value=fake_reranker) as reranker,
            patch.object(RagRails, "retrieve", return_value=expected) as retrieve,
        ):
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
        embedder.assert_called_once_with(provider="voyage", model="voyage-3", input_type="query")
        reranker.assert_called_once_with(provider="voyage", model="rerank-2-lite")
        retrieve.assert_called_once_with(
            "How do payouts work?",
            embedder=fake_embedder,
            vector_db="qdrant",
            collection="rag_chunks",
            url="http://localhost:6333",
            top_k=20,
            use_rerank=True,
            reranker=fake_reranker,
            rerank_top_k=5,
        )
        self.assertIn("Results: 1", result.output)
        self.assertIn("rerank=0.9700", result.output)


if __name__ == "__main__":
    unittest.main()
