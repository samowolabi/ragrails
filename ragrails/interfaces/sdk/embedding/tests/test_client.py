from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from ragrails.interfaces.sdk.embedding.client import EmbeddingMixin
from ragrails.models.embedder.config import EmbedderConfig as ModelEmbedderConfig


class SDK(EmbeddingMixin):
    pass


class FakeEmbedder:
    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _ in texts]

    @property
    def vector_size(self) -> int:
        return 1


class EmbeddingSDKTests(unittest.TestCase):
    def test_embedder_creates_model_object(self) -> None:
        fake_model = FakeEmbedder()

        with patch("ragrails.models.embedder.config.create_embedder", return_value=fake_model) as create_embedder:
            result = SDK().embedder(
                provider="voyage",
                model="voyage-3",
                input_type="document",
                options={"api_key": "test"},
            )

        self.assertIs(result, fake_model)
        model_config = create_embedder.call_args.args[0]
        self.assertIsInstance(model_config, ModelEmbedderConfig)
        self.assertEqual(model_config.provider, "voyage")
        self.assertEqual(model_config.model, "voyage-3")
        self.assertEqual(model_config.options, {"api_key": "test"})
        self.assertEqual(create_embedder.call_args.kwargs, {"input_type": "document"})

    def test_embed_returns_in_memory_result(self) -> None:
        chunks = [{"id": "one", "text": "hello", "metadata": {}}]
        fake_model = FakeEmbedder()
        stats = {
            "embedded": 1,
            "failed": 0,
            "outputs": [{"id": "one", "text": "hello", "embed_text": "hello", "embedding": [1.0]}],
            "errors": [],
        }

        with patch("ragrails.core.stg_03_embedder.embedder.embed_chunks", return_value=stats) as embed_chunks:
            result = SDK().embed(
                chunks=chunks,
                embedder=fake_model,
                batch_size=8,
            )

        embed_chunks.assert_called_once()
        self.assertIs(embed_chunks.call_args.kwargs["chunks"], chunks)
        self.assertIs(embed_chunks.call_args.kwargs["model"], fake_model)
        self.assertEqual(embed_chunks.call_args.kwargs["config"].batch_size, 8)

        self.assertEqual(result.inputs, 1)
        self.assertEqual(result.embedded, 1)
        self.assertEqual(result.items, stats["outputs"])
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.errors, [])

    def test_embed_preserves_core_errors(self) -> None:
        chunks = [{"id": "bad", "text": "", "metadata": {}}]
        stats = {
            "embedded": 0,
            "failed": 1,
            "outputs": [],
            "errors": [{"source": "bad", "stage": "validate", "error": "bad"}],
        }

        with patch("ragrails.core.stg_03_embedder.embedder.embed_chunks", return_value=stats):
            result = SDK().embed(chunks=chunks, embedder=FakeEmbedder())

        self.assertEqual(result.inputs, 1)
        self.assertEqual(result.embedded, 0)
        self.assertEqual(result.items, [])
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.errors, stats["errors"])

    def test_embed_wraps_missing_provider_dependency(self) -> None:
        with patch(
            "ragrails.models.embedder.config.create_embedder",
            Mock(side_effect=ImportError("missing provider")),
        ):
            with self.assertRaisesRegex(RuntimeError, "Embedding requires optional dependencies"):
                SDK().embedder(provider="voyage")

    def test_embed_rejects_non_list_chunks(self) -> None:
        with self.assertRaisesRegex(TypeError, "chunks must be a list"):
            SDK().embed(chunks={"text": "bad"}, embedder=FakeEmbedder())

    def test_embed_rejects_empty_chunks(self) -> None:
        with self.assertRaisesRegex(ValueError, "chunks must include at least one"):
            SDK().embed(chunks=[], embedder=FakeEmbedder())

    def test_embed_rejects_non_object_embedder(self) -> None:
        with self.assertRaisesRegex(TypeError, "embedding model object"):
            SDK().embed(chunks=[{"text": "hello"}], embedder="voyage")

    def test_embed_rejects_invalid_batch_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "batch_size must be greater than 0"):
            SDK().embed(chunks=[{"text": "hello"}], embedder=FakeEmbedder(), batch_size=0)

        with self.assertRaisesRegex(ValueError, "batch_size must be greater than 0"):
            SDK().embed(chunks=[{"text": "hello"}], embedder=FakeEmbedder(), batch_size=True)

    def test_embedder_rejects_required_strings(self) -> None:
        with self.assertRaisesRegex(ValueError, "provider is required"):
            SDK().embedder(provider="")

        with self.assertRaisesRegex(ValueError, "model is required"):
            SDK().embedder(model="")

        with self.assertRaisesRegex(ValueError, "input_type is required"):
            SDK().embedder(input_type="")

    def test_embedder_rejects_non_dict_options(self) -> None:
        with self.assertRaisesRegex(TypeError, "options must be a dictionary"):
            SDK().embedder(options=["bad"])


if __name__ == "__main__":
    unittest.main()
