from __future__ import annotations

import unittest
from unittest.mock import patch

from ragrails.interfaces.server.embedding.schemas import EmbedRequest
from ragrails.interfaces.server.embedding.services import embed_chunks
from ragrails.interfaces.sdk import RagRails
from ragrails.types import EmbedResult


class ServerEmbeddingServiceTests(unittest.TestCase):
    def test_embed_creates_embedder_and_calls_sdk(self) -> None:
        expected = EmbedResult(inputs=1, embedded=1, items=[{"id": "chunk-1", "embedding": [1.0]}], failed=0, errors=[])
        fake_embedder = object()

        with (
            patch.object(RagRails, "embedder", return_value=fake_embedder) as embedder,
            patch.object(RagRails, "embed", return_value=expected) as embed,
        ):
            result = embed_chunks(EmbedRequest(chunks=[{"id": "chunk-1", "text": "hello"}], provider="voyage", batch_size=16))

        embedder.assert_called_once_with(provider="voyage", model="voyage-3", input_type="document", options=None)
        embed.assert_called_once_with(chunks=[{"id": "chunk-1", "text": "hello"}], embedder=fake_embedder, batch_size=16)
        self.assertEqual(result["embedded"], 1)


if __name__ == "__main__":
    unittest.main()
