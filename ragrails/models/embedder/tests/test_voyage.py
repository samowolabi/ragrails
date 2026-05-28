from __future__ import annotations

import builtins
import os
import types
import unittest
from unittest.mock import patch

from ragrails.models.embedder.voyage import VoyageModel


class FakeVoyageClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.calls: list[dict] = []

    def embed(self, texts: list[str], *, model: str, input_type: str):
        self.calls.append({"texts": texts, "model": model, "input_type": input_type})
        embeddings = [[float(len(text))] for text in texts]
        return types.SimpleNamespace(embeddings=embeddings)


class VoyageModelTests(unittest.TestCase):
    def test_vector_size_uses_known_model_dimensions(self) -> None:
        self.assertEqual(VoyageModel(model_name="voyage-3-lite").vector_size, 512)
        self.assertEqual(VoyageModel(model_name="voyage-3").vector_size, 1024)
        self.assertEqual(VoyageModel(model_name="unknown-model").vector_size, 1024)

    def test_missing_dependency_has_clear_error(self) -> None:
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "voyageai":
                raise ImportError("No module named voyageai")
            return real_import(name, *args, **kwargs)

        with patch.object(builtins, "__import__", side_effect=fake_import):
            with self.assertRaisesRegex(RuntimeError, "Voyage embeddings require"):
                VoyageModel().encode(["hello"])

    def test_missing_api_key_has_clear_error(self) -> None:
        fake_module = types.SimpleNamespace(Client=FakeVoyageClient)

        with patch.dict("sys.modules", {"voyageai": fake_module}):
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, "VOYAGE_API_KEY"):
                    VoyageModel().encode(["hello"])

    def test_encode_batches_requests(self) -> None:
        created_clients: list[FakeVoyageClient] = []

        def client_factory(api_key: str) -> FakeVoyageClient:
            client = FakeVoyageClient(api_key)
            created_clients.append(client)
            return client

        fake_module = types.SimpleNamespace(Client=client_factory)

        with patch.dict("sys.modules", {"voyageai": fake_module}):
            with patch.dict(os.environ, {"VOYAGE_API_KEY": "test-key"}, clear=True):
                model = VoyageModel(model_name="voyage-3-lite", batch_size=2, input_type="query")
                result = model.encode(["alpha", "bravo", "charlie"])

        self.assertEqual(result, [[5.0], [5.0], [7.0]])
        self.assertEqual(len(created_clients), 1)
        self.assertEqual(created_clients[0].api_key, "test-key")
        self.assertEqual(created_clients[0].calls, [
            {"texts": ["alpha", "bravo"], "model": "voyage-3-lite", "input_type": "query"},
            {"texts": ["charlie"], "model": "voyage-3-lite", "input_type": "query"},
        ])


if __name__ == "__main__":
    unittest.main()
