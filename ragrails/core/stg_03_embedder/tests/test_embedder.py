from __future__ import annotations

import unittest

from ragrails.models.embedder.base import EmbeddingModel
from ragrails.core.stg_03_embedder.config import EmbedderConfig
from ragrails.core.stg_03_embedder.embedder import embed_chunks


class FakeModel(EmbeddingModel):
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(i), float(len(text))] for i, text in enumerate(texts)]

    @property
    def vector_size(self) -> int:
        return 2


class FailingModel(FakeModel):
    def encode(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("provider unavailable")


class BadCountModel(FakeModel):
    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 2.0]]


class EmbedderCoreTests(unittest.TestCase):
    def test_embed_chunks_returns_vectors_in_memory(self) -> None:
        model = FakeModel()
        chunks = [
            {
                "id": "chunk-1",
                "source": "manual://one",
                "text": "Visible text",
                "embed_text": "Embedding text",
                "metadata": {"id": "chunk-1", "source": "manual://one", "title": "One"},
            }
        ]

        result = embed_chunks(chunks=chunks, model=model, config=EmbedderConfig(batch_size=64))

        self.assertEqual(result["embedded"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["errors"], [])
        self.assertEqual(model.calls, [["Embedding text"]])
        self.assertEqual(result["outputs"], [
            {
                "id": "chunk-1",
                "source": "manual://one",
                "text": "Visible text",
                "embed_text": "Embedding text",
                "embedding": [0.0, 14.0],
                "metadata": {"id": "chunk-1", "source": "manual://one", "title": "One"},
            }
        ])

    def test_embed_chunks_batches_by_config(self) -> None:
        model = FakeModel()
        chunks = [
            {"id": "a", "text": "alpha", "metadata": {"id": "a"}},
            {"id": "b", "text": "bravo", "metadata": {"id": "b"}},
            {"id": "c", "text": "charlie", "metadata": {"id": "c"}},
        ]

        result = embed_chunks(chunks=chunks, model=model, config=EmbedderConfig(batch_size=2))

        self.assertEqual(result["embedded"], 3)
        self.assertEqual(model.calls, [["alpha", "bravo"], ["charlie"]])

    def test_embed_chunks_collects_validation_errors(self) -> None:
        model = FakeModel()
        result = embed_chunks(
            chunks=[
                {"source": "manual://bad", "text": ""},
                {"id": "good", "text": "good text", "metadata": {"id": "good"}},
            ],
            model=model,
        )

        self.assertEqual(result["embedded"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"], [
            {
                "source": "manual://bad",
                "source_kind": "chunk",
                "stage": "validate",
                "error": "chunk text must be a non-empty string",
                "isRetryable": False,
                "attempts": 1,
            }
        ])

    def test_embed_chunks_rejects_non_list_chunks(self) -> None:
        result = embed_chunks(chunks={"text": "bad"}, model=FakeModel())

        self.assertEqual(result, {
            "embedded": 0,
            "failed": 1,
            "outputs": [],
            "errors": [
                {
                    "source": "",
                    "source_kind": "chunk",
                    "stage": "validate",
                    "error": "chunks must be a list",
                    "isRetryable": False,
                    "attempts": 1,
                }
            ],
        })

    def test_embed_chunks_validates_config(self) -> None:
        result = embed_chunks(
            chunks=[],
            model=FakeModel(),
            config=EmbedderConfig(batch_size=0),
        )

        self.assertEqual(result["embedded"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"][0]["stage"], "validate")
        self.assertEqual(result["errors"][0]["error"], "batch_size must be greater than 0")

    def test_model_failure_marks_batch_retryable(self) -> None:
        result = embed_chunks(
            chunks=[{"source": "manual://one", "text": "text", "metadata": {}}],
            model=FailingModel(),
        )

        self.assertEqual(result["embedded"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"], [
            {
                "source": "manual://one",
                "source_kind": "chunk",
                "stage": "embed",
                "error": "provider unavailable",
                "isRetryable": True,
                "attempts": 1,
            }
        ])

    def test_vector_count_mismatch_is_retryable_embed_error(self) -> None:
        result = embed_chunks(
            chunks=[
                {"source": "manual://one", "text": "one", "metadata": {}},
                {"source": "manual://two", "text": "two", "metadata": {}},
            ],
            model=BadCountModel(),
        )

        self.assertEqual(result["embedded"], 0)
        self.assertEqual(result["failed"], 2)
        self.assertEqual(result["errors"][0]["stage"], "embed")
        self.assertTrue(result["errors"][0]["isRetryable"])


if __name__ == "__main__":
    unittest.main()
