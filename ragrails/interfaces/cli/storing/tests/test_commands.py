from __future__ import annotations

import json
import os
import unittest
from unittest.mock import patch

from click.testing import CliRunner

from ragrails.interfaces.cli.config import save_config
from ragrails.interfaces.cli.main import cli
from ragrails.interfaces.sdk import RagRails
from ragrails.types import DeleteResult, EditResult, StoreResult


class CliStoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_store_loads_embedded_chunks(self) -> None:
        expected = StoreResult(inputs=1, stored=1, items=[{"id": "chunk-1"}], failed=0, provider="qdrant", collection="rag_chunks", errors=[])

        with self.runner.isolated_filesystem():
            os.mkdir("embedded")
            with open("embedded/chunks.json", "w", encoding="utf-8") as file:
                json.dump([{"id": "chunk-1", "text": "hello", "embedding": [1.0]}], file)

            with patch.object(RagRails, "store", return_value=expected) as store:
                result = self.runner.invoke(cli, [
                    "store",
                    "--input-dir",
                    "embedded",
                    "--vector-db",
                    "qdrant",
                    "--collection",
                    "rag_chunks",
                    "--url",
                    "http://localhost:6333",
                    "--batch-size",
                    "16",
                ])

        self.assertEqual(result.exit_code, 0, result.output)
        store.assert_called_once_with(
            embedded_chunks=[{"id": "chunk-1", "text": "hello", "embedding": [1.0]}],
            batch_size=16,
        )
        self.assertIn("Stored     : 1", result.output)

    def test_edit_loads_chunks_and_creates_embedder(self) -> None:
        expected = EditResult(requested=1, edited=1, items=[{"id": "chunk-1"}], failed=0, provider="qdrant", collection="rag_chunks", errors=[])

        with self.runner.isolated_filesystem():
            os.mkdir("updates")
            with open("updates/chunk.json", "w", encoding="utf-8") as file:
                json.dump({"id": "chunk-1", "text": "updated"}, file)

            with patch.object(RagRails, "edit", return_value=expected) as edit:
                result = self.runner.invoke(cli, [
                    "edit",
                    "--input-dir",
                    "updates",
                    "--vector-db",
                    "qdrant",
                    "--collection",
                    "rag_chunks",
                    "--provider",
                    "voyage",
                    "--model",
                    "voyage-3",
                    "--batch-size",
                    "8",
                ])

        self.assertEqual(result.exit_code, 0, result.output)
        edit.assert_called_once_with(
            chunks=[{"id": "chunk-1", "text": "updated"}],
            batch_size=8,
        )
        self.assertIn("Edited     : 1", result.output)

    def test_delete_passes_ids_to_sdk(self) -> None:
        expected = DeleteResult(requested=2, deleted=2, items=[{"id": "chunk-1"}, {"id": "chunk-2"}], failed=0, provider="qdrant", collection="rag_chunks", errors=[])

        with self.runner.isolated_filesystem():
            with patch.object(RagRails, "delete", return_value=expected) as delete:
                result = self.runner.invoke(cli, [
                    "delete",
                    "--id",
                    "chunk-1",
                    "--id",
                    "chunk-2",
                    "--vector-db",
                    "qdrant",
                    "--collection",
                    "rag_chunks",
                ])

        self.assertEqual(result.exit_code, 0, result.output)
        delete.assert_called_once_with(ids=["chunk-1", "chunk-2"])
        self.assertIn("Deleted    : 2", result.output)

    def test_store_uses_advanced_batch_size_default(self) -> None:
        expected = StoreResult(inputs=1, stored=1, items=[{"id": "chunk-1"}], failed=0, provider="qdrant", collection="docs", errors=[])

        with self.runner.isolated_filesystem():
            save_config({"storage": {"batch_size": 48}})
            os.mkdir("embedded")
            with open("embedded/chunks.json", "w", encoding="utf-8") as file:
                json.dump([{"id": "chunk-1", "text": "hello", "embedding": [1.0]}], file)

            with patch.object(RagRails, "store", return_value=expected) as store:
                result = self.runner.invoke(cli, ["store", "--input-dir", "embedded"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(store.call_args.kwargs["batch_size"], 48)


if __name__ == "__main__":
    unittest.main()
