from __future__ import annotations

import unittest

from ragrails.core.stg_04_storing.lifecycle import delete_stored_chunks, edit_stored_chunks
from ragrails.models.embedder.base import EmbeddingModel
from ragrails.models.vector_db.base import Point, SearchResult, VectorStore


class FakeEmbedder(EmbeddingModel):
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(index + 1), float(len(text))] for index, text in enumerate(texts)]

    @property
    def vector_size(self) -> int:
        return 2


class BadCountEmbedder(FakeEmbedder):
    def encode(self, texts: list[str]) -> list[list[float]]:
        return []


class FakeStore(VectorStore):
    provider = "fake"
    collection = "test"

    def __init__(self, fail_delete: bool = False, fail_upsert: bool = False) -> None:
        self.fail_delete = fail_delete
        self.fail_upsert = fail_upsert
        self.deleted: list[list[str]] = []
        self.batches: list[list[Point]] = []

    def ensure_collection(self, vector_size: int) -> None:
        return None

    def upsert(self, points: list[Point]) -> None:
        if self.fail_upsert:
            raise RuntimeError("upsert unavailable")
        self.batches.append(points)

    def delete(self, ids: list[str]) -> None:
        if self.fail_delete:
            raise RuntimeError("delete unavailable")
        self.deleted.append(ids)

    def search(self, vector: list[float], top_k: int = 5) -> list[SearchResult]:
        return []


class LifecycleCoreTests(unittest.TestCase):
    def test_delete_stored_chunks_deletes_valid_ids(self) -> None:
        store = FakeStore()

        result = delete_stored_chunks(ids=["a", "b"], store=store)

        self.assertEqual(result, {
            "deleted": 2,
            "failed": 0,
            "outputs": [{"id": "a"}, {"id": "b"}],
            "errors": [],
        })
        self.assertEqual(store.deleted, [["a", "b"]])

    def test_delete_stored_chunks_reports_validation_errors(self) -> None:
        store = FakeStore()

        result = delete_stored_chunks(ids=["a", ""], store=store)

        self.assertEqual(result["deleted"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(store.deleted, [["a"]])
        self.assertEqual(result["errors"][0]["error"], "ids[1] must be a non-empty string")

    def test_delete_stored_chunks_reports_provider_error(self) -> None:
        result = delete_stored_chunks(ids=["a"], store=FakeStore(fail_delete=True))

        self.assertEqual(result["deleted"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"][0]["stage"], "delete")
        self.assertEqual(result["errors"][0]["error"], "delete unavailable")

    def test_edit_stored_chunks_embeds_and_upserts_replacements(self) -> None:
        embedder = FakeEmbedder()
        store = FakeStore()

        result = edit_stored_chunks(
            chunks=[
                {"id": "a", "text": "Alpha updated", "source": "manual://a", "metadata": {"title": "A"}},
                {"id": "b", "text": "Bravo updated", "metadata": {"source": "manual://b"}},
            ],
            embedder=embedder,
            store=store,
            batch_size=1,
        )

        self.assertEqual(result["edited"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(embedder.calls, [["Alpha updated", "Bravo updated"]])
        self.assertEqual([[point.id for point in batch] for batch in store.batches], [["a"], ["b"]])
        self.assertEqual(store.batches[0][0].payload, {"title": "A", "text": "Alpha updated", "source": "manual://a"})
        self.assertEqual(store.batches[0][0].vector, [1.0, 13.0])

    def test_edit_stored_chunks_collects_validation_errors(self) -> None:
        result = edit_stored_chunks(
            chunks=[
                {"id": "", "text": "Bad"},
                {"id": "good", "text": "Good"},
            ],
            embedder=FakeEmbedder(),
            store=FakeStore(),
        )

        self.assertEqual(result["edited"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"][0]["error"], "chunk id must be a non-empty string")

    def test_edit_stored_chunks_reports_embed_error(self) -> None:
        result = edit_stored_chunks(
            chunks=[{"id": "a", "text": "Alpha"}],
            embedder=BadCountEmbedder(),
            store=FakeStore(),
        )

        self.assertEqual(result["edited"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"][0]["stage"], "embed")
        self.assertEqual(result["errors"][0]["error"], "embedding model returned a different number of vectors than input chunks")

    def test_edit_stored_chunks_reports_upsert_error_per_point(self) -> None:
        result = edit_stored_chunks(
            chunks=[{"id": "a", "text": "Alpha", "source": "manual://a"}],
            embedder=FakeEmbedder(),
            store=FakeStore(fail_upsert=True),
        )

        self.assertEqual(result["edited"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"][0]["stage"], "upsert")
        self.assertEqual(result["errors"][0]["error"], "upsert unavailable")


if __name__ == "__main__":
    unittest.main()
