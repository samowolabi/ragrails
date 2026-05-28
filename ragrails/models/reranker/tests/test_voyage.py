from __future__ import annotations

import builtins
import os
import types
import unittest
from unittest.mock import patch

from ragrails.models.reranker.voyage import VoyageReranker


class FakeVoyageClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.calls: list[dict] = []

    def rerank(self, *, query: str, documents: list[str], model: str):
        self.calls.append({"query": query, "documents": documents, "model": model})
        results = [
            types.SimpleNamespace(index=1, relevance_score=0.9),
            types.SimpleNamespace(index=0, relevance_score=0.2),
        ]
        return types.SimpleNamespace(results=results)


class VoyageRerankerTests(unittest.TestCase):
    def test_missing_dependency_has_clear_error(self) -> None:
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "voyageai":
                raise ImportError("No module named voyageai")
            return real_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=fake_import):
            with self.assertRaisesRegex(RuntimeError, "Voyage reranking requires"):
                VoyageReranker().rerank("query", ["doc"])

    def test_missing_api_key_has_clear_error(self) -> None:
        fake_module = types.SimpleNamespace(Client=FakeVoyageClient)

        with patch.dict("sys.modules", {"voyageai": fake_module}):
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, "VOYAGE_API_KEY"):
                    VoyageReranker().rerank("query", ["doc"])

    def test_rerank_restores_input_order(self) -> None:
        created_clients: list[FakeVoyageClient] = []

        def client_factory(api_key: str) -> FakeVoyageClient:
            client = FakeVoyageClient(api_key)
            created_clients.append(client)
            return client

        fake_module = types.SimpleNamespace(Client=client_factory)

        with patch.dict("sys.modules", {"voyageai": fake_module}):
            with patch.dict(os.environ, {"VOYAGE_API_KEY": "test-key"}, clear=True):
                scores = VoyageReranker(model_name="rerank-2-lite").rerank("query", ["first", "second"])

        self.assertEqual(scores, [0.2, 0.9])
        self.assertEqual(len(created_clients), 1)
        self.assertEqual(created_clients[0].api_key, "test-key")
        self.assertEqual(created_clients[0].calls, [
            {"query": "query", "documents": ["first", "second"], "model": "rerank-2-lite"}
        ])


if __name__ == "__main__":
    unittest.main()
