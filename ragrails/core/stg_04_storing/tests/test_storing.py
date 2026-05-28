from __future__ import annotations

import unittest

from ragrails.models.vector_db.base import Point, SearchResult, VectorStore
from ragrails.core.stg_04_storing.config import StoringConfig
from ragrails.core.stg_04_storing.storing import store_embeddings


class FakeStore(VectorStore):
    provider = "fake"
    collection = "test"

    def __init__(self, fail_ensure: bool = False, fail_upsert: bool = False) -> None:
        self.fail_ensure = fail_ensure
        self.fail_upsert = fail_upsert
        self.vector_sizes: list[int] = []
        self.batches: list[list[Point]] = []

    def ensure_collection(self, vector_size: int) -> None:
        if self.fail_ensure:
            raise RuntimeError("collection unavailable")
        self.vector_sizes.append(vector_size)

    def upsert(self, points: list[Point]) -> None:
        if self.fail_upsert:
            raise RuntimeError("upsert unavailable")
        self.batches.append(points)

    def search(self, vector: list[float], top_k: int = 5) -> list[SearchResult]:
        return []


class StoringCoreTests(unittest.TestCase):
    def test_store_embeddings_upserts_points_in_batches(self) -> None:
        store = FakeStore()

        result = store_embeddings(
            embedded_chunks=[
                {
                    "id": "a",
                    "source": "manual://a",
                    "text": "Alpha",
                    "embedding": [1, 2],
                    "metadata": {"title": "A"},
                },
                {
                    "id": "b",
                    "source": "manual://b",
                    "text": "Bravo",
                    "embedding": [3.5, 4.5],
                    "metadata": {"title": "B"},
                },
                {
                    "id": "c",
                    "source": "manual://c",
                    "text": "Charlie",
                    "embedding": [5, 6],
                    "metadata": {"title": "C"},
                },
            ],
            store=store,
            config=StoringConfig(batch_size=2),
        )

        self.assertEqual(result, {
            "stored": 3,
            "failed": 0,
            "outputs": [
                {"id": "a", "source": "manual://a"},
                {"id": "b", "source": "manual://b"},
                {"id": "c", "source": "manual://c"},
            ],
            "errors": [],
        })
        self.assertEqual(store.vector_sizes, [2])
        self.assertEqual([[point.id for point in batch] for batch in store.batches], [["a", "b"], ["c"]])
        self.assertEqual(store.batches[0][0].payload, {"title": "A", "text": "Alpha", "source": "manual://a"})

    def test_store_embeddings_can_skip_ensure_collection(self) -> None:
        store = FakeStore()

        result = store_embeddings(
            embedded_chunks=[
                {"id": "a", "source": "manual://a", "text": "Alpha", "embedding": [1.0], "metadata": {}},
            ],
            store=store,
            config=StoringConfig(ensure_collection=False),
        )

        self.assertEqual(result["stored"], 1)
        self.assertEqual(store.vector_sizes, [])

    def test_store_embeddings_collects_validation_errors(self) -> None:
        store = FakeStore()

        result = store_embeddings(
            embedded_chunks=[
                {"id": "", "source": "manual://bad", "text": "Bad", "embedding": [1.0]},
                {"id": "good", "source": "manual://good", "text": "Good", "embedding": [2.0]},
            ],
            store=store,
        )

        self.assertEqual(result["stored"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"], [
            {
                "source": "manual://bad",
                "source_kind": "embedded_chunk",
                "stage": "validate",
                "error": "embedded chunk id must be a non-empty string",
                "isRetryable": False,
                "attempts": 1,
            }
        ])

    def test_store_embeddings_rejects_non_list_input(self) -> None:
        result = store_embeddings(embedded_chunks={"id": "bad"}, store=FakeStore())

        self.assertEqual(result, {
            "stored": 0,
            "failed": 1,
            "outputs": [],
            "errors": [
                {
                    "source": "",
                    "source_kind": "embedded_chunk",
                    "stage": "validate",
                    "error": "embedded_chunks must be a list",
                    "isRetryable": False,
                    "attempts": 1,
                }
            ],
        })

    def test_store_embeddings_skips_mismatched_vector_sizes(self) -> None:
        store = FakeStore()

        result = store_embeddings(
            embedded_chunks=[
                {"id": "a", "source": "manual://a", "text": "Alpha", "embedding": [1.0, 2.0]},
                {"id": "b", "source": "manual://b", "text": "Bravo", "embedding": [3.0]},
            ],
            store=store,
        )

        self.assertEqual(result["stored"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual([point.id for batch in store.batches for point in batch], ["a"])
        self.assertEqual(result["errors"], [
            {
                "source": "manual://b",
                "source_kind": "embedded_chunk",
                "stage": "validate",
                "error": "embedding vector size does not match the first valid embedding",
                "isRetryable": False,
                "attempts": 1,
            }
        ])

    def test_store_embeddings_reports_ensure_collection_failure(self) -> None:
        result = store_embeddings(
            embedded_chunks=[
                {"id": "a", "source": "manual://a", "text": "Alpha", "embedding": [1.0]},
            ],
            store=FakeStore(fail_ensure=True),
        )

        self.assertEqual(result["stored"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"], [
            {
                "source": "",
                "source_kind": "embedded_chunk",
                "stage": "ensure_collection",
                "error": "collection unavailable",
                "isRetryable": True,
                "attempts": 1,
            }
        ])

    def test_store_embeddings_reports_upsert_failure_per_point(self) -> None:
        result = store_embeddings(
            embedded_chunks=[
                {"id": "a", "source": "manual://a", "text": "Alpha", "embedding": [1.0]},
                {"id": "b", "source": "manual://b", "text": "Bravo", "embedding": [2.0]},
            ],
            store=FakeStore(fail_upsert=True),
            config=StoringConfig(batch_size=2),
        )

        self.assertEqual(result["stored"], 0)
        self.assertEqual(result["failed"], 2)
        self.assertEqual(result["errors"], [
            {
                "source": "manual://a",
                "source_kind": "embedded_chunk",
                "stage": "upsert",
                "error": "upsert unavailable",
                "isRetryable": True,
                "attempts": 1,
            },
            {
                "source": "manual://b",
                "source_kind": "embedded_chunk",
                "stage": "upsert",
                "error": "upsert unavailable",
                "isRetryable": True,
                "attempts": 1,
            },
        ])


if __name__ == "__main__":
    unittest.main()
