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
            items=[RetrievedChunk(id="chunk-1", score=0.9, text="hello", metadata={})],
            failed=0,
            errors=[],
        )
        fake_embedder = object()
        fake_reranker = object()

        with (
            patch.object(RagRails, "embedder", return_value=fake_embedder) as embedder,
            patch.object(RagRails, "reranker", return_value=fake_reranker) as reranker,
            patch.object(RagRails, "retrieve", return_value=expected) as retrieve,
        ):
            result = retrieve_chunks(RetrieveRequest(query="auth", collection="docs", use_rerank=True))

        embedder.assert_called_once_with(provider="voyage", model="voyage-3", input_type="query", options=None)
        reranker.assert_called_once_with(provider="voyage", model="rerank-2-lite", options=None)
        self.assertIs(retrieve.call_args.kwargs["embedder"], fake_embedder)
        self.assertIs(retrieve.call_args.kwargs["reranker"], fake_reranker)
        self.assertEqual(result["retrieved"], 1)


if __name__ == "__main__":
    unittest.main()
