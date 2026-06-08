from __future__ import annotations

import unittest
from unittest.mock import patch

from ragrails.interfaces.server.retrieval.schemas import RetrieveRequest
from ragrails.interfaces.server.retrieval.services import retrieve_chunks
from ragrails.interfaces.sdk import RagRails
from ragrails.types import RetrievedChunk, RetrieveResult


class ServerRetrievalServiceTests(unittest.TestCase):
    def test_retrieve_creates_models_and_calls_sdk(self) -> None:
        expected = RetrieveResult(
            query="auth",
            search_query="auth",
            retrieved=1,
            items=[RetrievedChunk(id="point-1", chunk_id="chunk-1", score=0.9, text="hello", metadata={})],
            failed=0,
            errors=[],
        )
        with patch.object(RagRails, "retrieve", return_value=expected) as retrieve:
            result = retrieve_chunks(RetrieveRequest(query="auth", collection="docs", use_rerank=True))

        self.assertEqual(retrieve.call_args.args, ("auth",))
        self.assertTrue(retrieve.call_args.kwargs["use_rerank"])
        self.assertEqual(result["retrieved"], 1)
        self.assertEqual(result["items"][0]["chunk_id"], "chunk-1")


if __name__ == "__main__":
    unittest.main()
