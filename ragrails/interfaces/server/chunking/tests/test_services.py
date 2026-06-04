from __future__ import annotations

import unittest
from unittest.mock import patch

from ragrails.interfaces.server.chunking.schemas import ChunkRequest
from ragrails.interfaces.server.chunking.services import chunk_dir
from ragrails.interfaces.sdk import RagRails
from ragrails.types import ChunkResult


class ServerChunkingServiceTests(unittest.TestCase):
    def test_chunk_calls_sdk(self) -> None:
        expected = ChunkResult(inputs=1, chunks=1, items=[{"id": "chunk-1"}], failed=0, errors=[])

        with patch.object(RagRails, "chunk", return_value=expected) as chunk:
            result = chunk_dir(ChunkRequest(markdown="hello", chunk_size=500))

        chunk.assert_called_once()
        self.assertEqual(chunk.call_args.kwargs["markdown"], "hello")
        self.assertEqual(chunk.call_args.kwargs["chunk_size"], 500)
        self.assertEqual(result["chunks"], 1)


if __name__ == "__main__":
    unittest.main()
