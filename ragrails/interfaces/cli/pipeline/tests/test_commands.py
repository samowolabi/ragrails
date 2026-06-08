from __future__ import annotations

import unittest
from unittest.mock import patch

from click.testing import CliRunner

from ragrails.interfaces.cli.main import cli
from ragrails.interfaces.sdk import RagRails
from ragrails.types import IngestPipelineResult, RetrieveResult


class CliPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_ingest_passes_pipeline_config_to_sdk(self) -> None:
        expected = IngestPipelineResult(
            sources=1,
            chunks=1,
            embedded=1,
            stored=1,
            source_results={},
            chunk_result=None,
            embed_result=None,
            store_result=None,
            failed=0,
            errors=[],
        )

        with self.runner.isolated_filesystem():
            with patch.object(RagRails, "ingest", return_value=expected) as ingest:
                result = self.runner.invoke(cli, [
                    "ingest",
                    "--markdown",
                    "hello",
                    "--vector-db",
                    "qdrant",
                    "--collection",
                    "rag_chunks",
                    "--url",
                    "http://localhost:6333",
                    "--provider",
                    "voyage",
                    "--model",
                    "voyage-3",
                    "--batch-size",
                    "16",
                    "--chunk-size",
                    "500",
                    "--chunk-overlap",
                    "50",
                    "--min-chunk-length",
                    "20",
                    "--concurrency",
                    "parallel",
                ])

        self.assertEqual(result.exit_code, 0, result.output)
        ingest.assert_called_once_with(
            markdown=["hello"],
            docs=None,
            urls=None,
            api=None,
            chunking={"chunk_size": 500, "chunk_overlap": 50, "min_chunk_length": 20},
            embedding={"batch_size": 16},
            storage={"batch_size": 16},
            concurrency="parallel",
        )
        self.assertIn("Stored   : 1", result.output)

    def test_query_passes_pipeline_config_to_sdk(self) -> None:
        expected = RetrieveResult(query="How do payouts work?", search_query="How do payouts work?", retrieved=0, items=[], failed=0, errors=[])

        with self.runner.isolated_filesystem():
            with patch.object(RagRails, "query", return_value=expected) as query:
                result = self.runner.invoke(cli, [
                    "query",
                    "How do payouts work?",
                    "--vector-db",
                    "qdrant",
                    "--collection",
                    "rag_chunks",
                    "--url",
                    "http://localhost:6333",
                    "--top-k",
                    "5",
                ])

        self.assertEqual(result.exit_code, 0, result.output)
        query.assert_called_once_with(
            "How do payouts work?",
            retrieval={"top_k": 5, "rerank": {"enabled": False}},
        )
        self.assertIn("Results: 0", result.output)


if __name__ == "__main__":
    unittest.main()
