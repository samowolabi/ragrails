from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from click.testing import CliRunner

from ragrails.interfaces.cli.config import save_config
from ragrails.interfaces.cli.main import cli
from ragrails.interfaces.sdk import RagRails
from ragrails.types import ChunkResult


class CliChunkingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_chunk_command_loads_ingestion_json_and_writes_chunks(self) -> None:
        with self.runner.isolated_filesystem():
            os.mkdir("ingestion")
            with open("ingestion/docs.json", "w", encoding="utf-8") as file:
                json.dump([
                    {
                        "text": "# CLI Test Guide\n\nThis command verifies file-based chunking.",
                        "source": "https://example.com/cli-test",
                        "metadata": {"title": "CLI Test Guide"},
                    }
                ], file)

            result = self.runner.invoke(cli, [
                "chunk",
                "--input-dir",
                "ingestion",
                "--output-dir",
                "chunks",
                "--chunk-size",
                "400",
                "--chunk-overlap",
                "40",
                "--min-chunk-length",
                "20",
            ])

            with open("chunks/chunks.json", encoding="utf-8") as file:
                chunks = json.load(file)

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["metadata"]["title"], "CLI Test Guide")
        self.assertIn("Saved to  : chunks/chunks.json", result.output)

    def test_chunk_uses_advanced_config_defaults(self) -> None:
        expected = ChunkResult(inputs=1, chunks=1, items=[{"id": "chunk-1", "text": "hello"}], failed=0, errors=[])

        with self.runner.isolated_filesystem():
            save_config({"chunking": {"chunk_size": 900, "chunk_overlap": 90, "min_chunk_length": 30}})
            os.mkdir("ingestion")
            with open("ingestion/docs.json", "w", encoding="utf-8") as file:
                json.dump([{"text": "hello", "metadata": {}}], file)

            with patch.object(RagRails, "chunk", return_value=expected) as chunk:
                result = self.runner.invoke(cli, ["chunk", "--input-dir", "ingestion", "--output-dir", "chunks"])

        self.assertEqual(result.exit_code, 0, result.output)
        chunk.assert_called_once_with(
            markdown=[{"text": "hello", "metadata": {}}],
            chunk_size=900,
            chunk_overlap=90,
            min_chunk_length=30,
        )

    def test_chunk_flags_override_advanced_config_defaults(self) -> None:
        expected = ChunkResult(inputs=1, chunks=1, items=[{"id": "chunk-1", "text": "hello"}], failed=0, errors=[])

        with self.runner.isolated_filesystem():
            save_config({"chunking": {"chunk_size": 900, "chunk_overlap": 90, "min_chunk_length": 30}})
            os.mkdir("ingestion")
            with open("ingestion/docs.json", "w", encoding="utf-8") as file:
                json.dump([{"text": "hello", "metadata": {}}], file)

            with patch.object(RagRails, "chunk", return_value=expected) as chunk:
                result = self.runner.invoke(cli, [
                    "chunk",
                    "--input-dir",
                    "ingestion",
                    "--output-dir",
                    "chunks",
                    "--chunk-size",
                    "400",
                    "--chunk-overlap",
                    "40",
                    "--min-chunk-length",
                    "20",
                ])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(chunk.call_args.kwargs["chunk_size"], 400)
        self.assertEqual(chunk.call_args.kwargs["chunk_overlap"], 40)
        self.assertEqual(chunk.call_args.kwargs["min_chunk_length"], 20)


if __name__ == "__main__":
    unittest.main()
