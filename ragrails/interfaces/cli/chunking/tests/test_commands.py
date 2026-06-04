from __future__ import annotations

import json
import os
import unittest

from click.testing import CliRunner

from ragrails.interfaces.cli.main import cli


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


if __name__ == "__main__":
    unittest.main()
