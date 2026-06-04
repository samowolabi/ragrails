from __future__ import annotations

import unittest

from ragrails.models.vector_db.base import Point, SearchResult, VectorStore
from ragrails.models.vector_db.config import VectorStoreConfig, create_store
from ragrails.models.vector_db.registry import (
    VECTOR_STORE_SPECS,
    create_vector_store,
    list_vector_stores,
    register_vector_store,
)


class FakeVectorStore(VectorStore):
    provider = "fake"

    def __init__(self, url: str, collection: str, namespace: str = "") -> None:
        self.url = url
        self.collection = collection
        self.namespace = namespace

    def ensure_collection(self, vector_size: int) -> None:
        return None

    def upsert(self, points: list[Point]) -> None:
        return None

    def delete(self, ids: list[str]) -> None:
        return None

    def search(self, vector: list[float], top_k: int = 5) -> list[SearchResult]:
        return []


class VectorStoreRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_specs = dict(VECTOR_STORE_SPECS)

    def tearDown(self) -> None:
        VECTOR_STORE_SPECS.clear()
        VECTOR_STORE_SPECS.update(self._original_specs)

    def test_lists_registered_vector_stores(self) -> None:
        providers = [info.provider for info in list_vector_stores()]

        self.assertIn("qdrant", providers)
        self.assertIn("pinecone", providers)
        self.assertIn("weaviate", providers)

    def test_registers_custom_vector_store_provider(self) -> None:
        register_vector_store(
            "fake",
            FakeVectorStore,
            default_url="http://localhost:9999",
            default_collection="fake_chunks",
        )

        store = create_vector_store("fake")

        self.assertIsInstance(store, FakeVectorStore)
        self.assertEqual(store.url, "http://localhost:9999")
        self.assertEqual(store.collection, "fake_chunks")

    def test_create_vector_store_accepts_options(self) -> None:
        register_vector_store(
            "fake",
            FakeVectorStore,
            default_url="http://localhost:9999",
            default_collection="fake_chunks",
        )

        store = create_vector_store(
            "fake",
            url="http://custom",
            collection="custom_chunks",
            namespace="tenant-a",
        )

        self.assertEqual(store.url, "http://custom")
        self.assertEqual(store.collection, "custom_chunks")
        self.assertEqual(store.namespace, "tenant-a")

    def test_config_create_store_uses_registry(self) -> None:
        register_vector_store(
            "fake",
            FakeVectorStore,
            default_url="http://localhost:9999",
            default_collection="fake_chunks",
        )

        store = create_store(VectorStoreConfig(provider="fake", url="http://config", collection="config_chunks"))

        self.assertIsInstance(store, FakeVectorStore)
        self.assertEqual(store.url, "http://config")
        self.assertEqual(store.collection, "config_chunks")

    def test_rejects_duplicate_provider_without_replace(self) -> None:
        register_vector_store("fake", FakeVectorStore, default_collection="fake_chunks")

        with self.assertRaisesRegex(ValueError, "already registered"):
            register_vector_store("fake", FakeVectorStore, default_collection="fake_chunks")

    def test_unknown_provider_error_lists_available_providers(self) -> None:
        with self.assertRaisesRegex(ValueError, "Available providers: pinecone, qdrant, weaviate"):
            create_vector_store("missing")


if __name__ == "__main__":
    unittest.main()
