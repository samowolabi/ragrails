from __future__ import annotations

import unittest

from ragrails.models.reranker.base import Reranker
from ragrails.models.reranker.config import RerankerConfig, create_reranker
from ragrails.models.reranker.registry import (
    RERANKER_SPECS,
    create_reranker as create_registered_reranker,
    list_rerankers,
    register_reranker,
)


class FakeReranker(Reranker):
    def __init__(self, model_name: str, bias: float = 0.0) -> None:
        self.model_name = model_name
        self.bias = bias

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        return [float(len(text)) + self.bias for text in texts]


class RerankerRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_specs = dict(RERANKER_SPECS)

    def tearDown(self) -> None:
        RERANKER_SPECS.clear()
        RERANKER_SPECS.update(self._original_specs)

    def test_lists_registered_rerankers(self) -> None:
        providers = [info.provider for info in list_rerankers()]

        self.assertIn("bm25", providers)
        self.assertIn("voyage", providers)

    def test_registers_custom_reranker_provider(self) -> None:
        register_reranker(
            "fake",
            FakeReranker,
            default_model="fake-rerank",
            models=("fake-rerank",),
        )

        model = create_registered_reranker("fake", bias=2.0)

        self.assertIsInstance(model, FakeReranker)
        self.assertEqual(model.model_name, "fake-rerank")
        self.assertEqual(model.rerank("q", ["abc"]), [5.0])

    def test_config_create_reranker_uses_registry(self) -> None:
        register_reranker(
            "fake",
            FakeReranker,
            default_model="fake-rerank",
            models=("fake-rerank",),
        )

        model = create_reranker(RerankerConfig(provider="fake", model="fake-large", options={"bias": 3.0}))

        self.assertIsInstance(model, FakeReranker)
        self.assertEqual(model.model_name, "fake-large")
        self.assertEqual(model.rerank("q", ["abcd"]), [7.0])

    def test_rejects_duplicate_provider_without_replace(self) -> None:
        register_reranker("fake", FakeReranker, default_model="fake-rerank")

        with self.assertRaisesRegex(ValueError, "already registered"):
            register_reranker("fake", FakeReranker, default_model="fake-rerank")

    def test_unknown_provider_error_lists_available_providers(self) -> None:
        with self.assertRaisesRegex(ValueError, "Available providers: bm25, voyage"):
            create_registered_reranker("missing")


if __name__ == "__main__":
    unittest.main()
