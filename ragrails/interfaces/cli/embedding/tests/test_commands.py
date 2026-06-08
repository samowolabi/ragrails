from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from click.testing import CliRunner

from ragrails.interfaces.cli.config import save_config
from ragrails.interfaces.cli.main import cli
from ragrails.interfaces.sdk import RagRails
from ragrails.types import EmbedResult


class CliEmbeddingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_embed_loads_chunks_and_writes_embedded_json(self) -> None:
        expected = EmbedResult(
            inputs=1,
            embedded=1,
            items=[{"id": "chunk-1", "text": "hello", "embedding": [1.0]}],
            failed=0,
            errors=[],
        )
        with self.runner.isolated_filesystem():
            os.mkdir("chunks")
            with open("chunks/guide.json", "w", encoding="utf-8") as file:
                json.dump([{"id": "chunk-1", "text": "hello", "metadata": {}}], file)

            with patch.object(RagRails, "embed", return_value=expected) as embed:
                result = self.runner.invoke(cli, [
                    "embed",
                    "--input-dir",
                    "chunks",
                    "--output-dir",
                    "embedded",
                    "--batch-size",
                    "16",
                    "--provider",
                    "voyage",
                    "--model",
                    "voyage-3",
                ])

            with open("embedded/embedded.json", encoding="utf-8") as file:
                saved = json.load(file)

        self.assertEqual(result.exit_code, 0, result.output)
        embed.assert_called_once_with(
            chunks=[{"id": "chunk-1", "text": "hello", "metadata": {}}],
            batch_size=16,
        )
        self.assertEqual(saved, expected.items)
        self.assertIn("Embedded : 1", result.output)

    def test_embed_uses_advanced_batch_size_default(self) -> None:
        expected = EmbedResult(
            inputs=1,
            embedded=1,
            items=[{"id": "chunk-1", "text": "hello", "embedding": [1.0]}],
            failed=0,
            errors=[],
        )
        with self.runner.isolated_filesystem():
            save_config({"embedding": {"provider": "voyage", "model": "voyage-3", "batch_size": 32}})
            os.mkdir("chunks")
            with open("chunks/guide.json", "w", encoding="utf-8") as file:
                json.dump([{"id": "chunk-1", "text": "hello", "metadata": {}}], file)

            with patch.object(RagRails, "embed", return_value=expected) as embed:
                result = self.runner.invoke(cli, [
                    "embed",
                    "--input-dir",
                    "chunks",
                    "--output-dir",
                    "embedded",
                ])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(embed.call_args.kwargs["batch_size"], 32)


if __name__ == "__main__":
    unittest.main()
