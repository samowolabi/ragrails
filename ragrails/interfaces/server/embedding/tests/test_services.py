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
        with patch.object(RagRails, "embed", return_value=expected) as embed:
            result = embed_chunks(EmbedRequest(chunks=[{"id": "chunk-1", "text": "hello"}], provider="voyage", batch_size=16))

        embed.assert_called_once_with(chunks=[{"id": "chunk-1", "text": "hello"}], input_type="document", batch_size=16)
        self.assertEqual(result["embedded"], 1)


if __name__ == "__main__":
    unittest.main()
