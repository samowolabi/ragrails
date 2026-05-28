from __future__ import annotations

import unittest

from ragrails.models.embedder.base import EmbeddingModel
from ragrails.models.embedder.config import EmbedderConfig, create_embedder
from ragrails.models.embedder.registry import (
    EMBEDDER_SPECS,
    create_embedder as create_registered_embedder,
    list_embedders,
    register_embedder,
)


class FakeEmbedder(EmbeddingModel):
    def __init__(self, model_name: str, input_type: str = "document", scale: float = 1.0) -> None:
        self.model_name = model_name
        self.input_type = input_type
        self.scale = scale

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[len(text) * self.scale] for text in texts]

    @property
    def vector_size(self) -> int:
        return 1


class EmbedderRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_specs = dict(EMBEDDER_SPECS)

    def tearDown(self) -> None:
        EMBEDDER_SPECS.clear()
        EMBEDDER_SPECS.update(self._original_specs)

    def test_lists_registered_embedders(self) -> None:
        providers = [info.provider for info in list_embedders()]

        self.assertIn("voyage", providers)

    def test_registers_custom_embedder_provider(self) -> None:
        register_embedder(
            "fake",
            FakeEmbedder,
            default_model="fake-small",
            models=("fake-small",),
        )

        model = create_registered_embedder("fake", input_type="query", scale=2.0)

        self.assertIsInstance(model, FakeEmbedder)
        self.assertEqual(model.model_name, "fake-small")
        self.assertEqual(model.input_type, "query")
        self.assertEqual(model.encode(["abcd"]), [[8.0]])

    def test_config_create_embedder_uses_registry(self) -> None:
        register_embedder(
            "fake",
            FakeEmbedder,
            default_model="fake-small",
            models=("fake-small",),
        )

        model = create_embedder(
            EmbedderConfig(provider="fake", model="fake-large", options={"scale": 3.0}),
            input_type="document",
        )

        self.assertIsInstance(model, FakeEmbedder)
        self.assertEqual(model.model_name, "fake-large")
        self.assertEqual(model.input_type, "document")
        self.assertEqual(model.encode(["abc"]), [[9.0]])

    def test_rejects_duplicate_provider_without_replace(self) -> None:
        register_embedder("fake", FakeEmbedder, default_model="fake-small")

        with self.assertRaisesRegex(ValueError, "already registered"):
            register_embedder("fake", FakeEmbedder, default_model="fake-small")

    def test_unknown_provider_error_lists_available_providers(self) -> None:
        with self.assertRaisesRegex(ValueError, "Available providers: voyage"):
            create_registered_embedder("missing")


if __name__ == "__main__":
    unittest.main()
