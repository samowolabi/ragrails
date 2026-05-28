from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from ragrails.interfaces.sdk.storing.client import StoringMixin


class SDK(StoringMixin):
    pass


class FakeStore:
    collection = "docs"


def _embedded_chunk() -> dict:
    return {
        "id": "chunk-1",
        "source": "guide.md",
        "text": "Chunk text",
        "embed_text": "Chunk text",
        "embedding": [0.1, 0.2],
        "metadata": {"title": "Guide"},
    }


class StoringSDKTests(unittest.TestCase):
    def test_store_returns_in_memory_result(self) -> None:
        embedded_chunks = [_embedded_chunk()]
        stats = {
            "stored": 1,
            "failed": 0,
            "outputs": [{"id": "chunk-1", "source": "guide.md"}],
            "errors": [],
        }

        with (
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()) as create_store,
            patch("ragrails.core.stg_04_storing.storing.store_embeddings", return_value=stats) as store_embeddings,
        ):
            result = SDK().store(
                embedded_chunks=embedded_chunks,
                vector_db="qdrant",
                collection="docs",
                url="http://localhost:6333",
                batch_size=32,
                ensure_collection=False,
                options={"api_key": "test"},
            )

        create_store.assert_called_once_with(
            provider="qdrant",
            url="http://localhost:6333",
            collection="docs",
            api_key="test",
        )
        store_embeddings.assert_called_once()
        self.assertIs(store_embeddings.call_args.kwargs["embedded_chunks"], embedded_chunks)
        self.assertEqual(store_embeddings.call_args.kwargs["config"].batch_size, 32)
        self.assertFalse(store_embeddings.call_args.kwargs["config"].ensure_collection)

        self.assertEqual(result.inputs, 1)
        self.assertEqual(result.stored, 1)
        self.assertEqual(result.items, stats["outputs"])
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.provider, "qdrant")
        self.assertEqual(result.collection, "docs")
        self.assertEqual(result.errors, [])

    def test_store_preserves_core_errors(self) -> None:
        error = {"source": "guide.md", "stage": "upsert", "error": "failed"}
        stats = {"stored": 0, "failed": 1, "outputs": [], "errors": [error]}

        with (
            patch("ragrails.models.vector_db.registry.create_vector_store", return_value=FakeStore()),
            patch("ragrails.core.stg_04_storing.storing.store_embeddings", return_value=stats),
        ):
            result = SDK().store(embedded_chunks=[_embedded_chunk()], vector_db="qdrant")

        self.assertEqual(result.inputs, 1)
        self.assertEqual(result.stored, 0)
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.items, [])
        self.assertEqual(result.errors, [error])

    def test_store_wraps_missing_provider_dependency(self) -> None:
        with patch(
            "ragrails.models.vector_db.registry.create_vector_store",
            Mock(side_effect=ImportError("missing qdrant")),
        ):
            with self.assertRaisesRegex(RuntimeError, "Storage requires optional dependencies"):
                SDK().store(embedded_chunks=[_embedded_chunk()], vector_db="qdrant")

    def test_store_rejects_non_list_embedded_chunks(self) -> None:
        with self.assertRaisesRegex(TypeError, "embedded_chunks must be a list"):
            SDK().store(embedded_chunks={"id": "bad"})

    def test_store_rejects_empty_embedded_chunks(self) -> None:
        with self.assertRaisesRegex(ValueError, "embedded_chunks must include at least one"):
            SDK().store(embedded_chunks=[])

    def test_store_rejects_invalid_vector_db(self) -> None:
        with self.assertRaisesRegex(ValueError, "vector_db must be one of"):
            SDK().store(embedded_chunks=[_embedded_chunk()], vector_db="redis")

    def test_store_rejects_invalid_batch_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "batch_size must be greater than 0"):
            SDK().store(embedded_chunks=[_embedded_chunk()], batch_size=0)

        with self.assertRaisesRegex(ValueError, "batch_size must be greater than 0"):
            SDK().store(embedded_chunks=[_embedded_chunk()], batch_size=True)

    def test_store_rejects_invalid_ensure_collection(self) -> None:
        with self.assertRaisesRegex(TypeError, "ensure_collection must be a boolean"):
            SDK().store(embedded_chunks=[_embedded_chunk()], ensure_collection="yes")

    def test_store_rejects_non_dict_options(self) -> None:
        with self.assertRaisesRegex(TypeError, "options must be a dictionary"):
            SDK().store(embedded_chunks=[_embedded_chunk()], options=["bad"])

    def test_store_validates_provider_collection_rules(self) -> None:
        with self.assertRaisesRegex(ValueError, "Pinecone"):
            SDK().store(embedded_chunks=[_embedded_chunk()], vector_db="pinecone", collection="bad_name")

        with self.assertRaisesRegex(ValueError, "Weaviate"):
            SDK().store(embedded_chunks=[_embedded_chunk()], vector_db="weaviate", collection="bad-name")

        with self.assertRaisesRegex(ValueError, "Weaviate"):
            SDK().store(embedded_chunks=[_embedded_chunk()], vector_db="weaviate", collection="ragchunks")


if __name__ == "__main__":
    unittest.main()
