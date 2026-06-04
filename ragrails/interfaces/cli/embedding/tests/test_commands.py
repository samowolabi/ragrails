from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from click.testing import CliRunner

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
        fake_embedder = object()

        with self.runner.isolated_filesystem():
            os.mkdir("chunks")
            with open("chunks/guide.json", "w", encoding="utf-8") as file:
                json.dump([{"id": "chunk-1", "text": "hello", "metadata": {}}], file)

            with (
                patch.object(RagRails, "embedder", return_value=fake_embedder) as embedder,
                patch.object(RagRails, "embed", return_value=expected) as embed,
            ):
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
        embedder.assert_called_once_with(provider="voyage", model="voyage-3", input_type="document")
        embed.assert_called_once_with(
            chunks=[{"id": "chunk-1", "text": "hello", "metadata": {}}],
            embedder=fake_embedder,
            batch_size=16,
        )
        self.assertEqual(saved, expected.items)
        self.assertIn("Embedded : 1", result.output)


if __name__ == "__main__":
    unittest.main()
