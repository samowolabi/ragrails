from __future__ import annotations

import importlib
import sys
import types
import unittest


class VectorStoreLifecycleAdapterTests(unittest.TestCase):
    def test_qdrant_delete_uses_point_ids(self) -> None:
        qdrant_client = types.ModuleType("qdrant_client")
        qdrant_models = types.ModuleType("qdrant_client.models")

        class FakeQdrantClient:
            pass

        class FakePointIdsList:
            def __init__(self, points):
                self.points = points

        class FakePointStruct:
            def __init__(self, id, vector, payload):
                self.id = id
                self.vector = vector
                self.payload = payload

        class FakeVectorParams:
            def __init__(self, size, distance):
                self.size = size
                self.distance = distance

        class FakeDistance:
            COSINE = "Cosine"

        qdrant_client.QdrantClient = FakeQdrantClient
        qdrant_models.Distance = FakeDistance
        qdrant_models.PointIdsList = FakePointIdsList
        qdrant_models.PointStruct = FakePointStruct
        qdrant_models.VectorParams = FakeVectorParams

        original_client = sys.modules.get("qdrant_client")
        original_models = sys.modules.get("qdrant_client.models")
        try:
            sys.modules["qdrant_client"] = qdrant_client
            sys.modules["qdrant_client.models"] = qdrant_models
            module = importlib.import_module("ragrails.models.vector_db.qdrant")
            module = importlib.reload(module)

            store = module.QdrantStore(collection="docs")
            calls = []
            store._get_client = lambda: types.SimpleNamespace(  # type: ignore[method-assign]
                delete=lambda **kwargs: calls.append(kwargs)
            )

            store.delete(["chunk-1", "chunk-2"])

            self.assertEqual(calls[0]["collection_name"], "docs")
            self.assertEqual(calls[0]["points_selector"].points, ["chunk-1", "chunk-2"])
        finally:
            if original_client is None:
                sys.modules.pop("qdrant_client", None)
            else:
                sys.modules["qdrant_client"] = original_client
            if original_models is None:
                sys.modules.pop("qdrant_client.models", None)
            else:
                sys.modules["qdrant_client.models"] = original_models

    def test_pinecone_delete_uses_ids_and_namespace(self) -> None:
        from ragrails.models.vector_db.pinecone import PineconeStore

        calls = []
        store = PineconeStore(collection="docs", namespace="tenant-a")
        store._get_index = lambda: types.SimpleNamespace(  # type: ignore[method-assign]
            delete=lambda **kwargs: calls.append(kwargs)
        )

        store.delete(["chunk-1"])

        self.assertEqual(calls, [{"ids": ["chunk-1"], "namespace": "tenant-a"}])

    def test_weaviate_delete_maps_ids_to_deterministic_uuids(self) -> None:
        from ragrails.models.vector_db.weaviate import WeaviateStore

        deleted = []
        data = types.SimpleNamespace(delete_by_id=lambda item_id: deleted.append(item_id))
        collection = types.SimpleNamespace(data=data)
        client = types.SimpleNamespace(collections=types.SimpleNamespace(get=lambda name: collection))
        store = WeaviateStore(collection="Docs")
        store._get_client = lambda: client  # type: ignore[method-assign]

        store.delete(["chunk-1"])

        self.assertEqual(deleted, [store._uuid_for("chunk-1")])


if __name__ == "__main__":
    unittest.main()
