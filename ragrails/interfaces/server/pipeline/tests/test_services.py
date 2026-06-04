from __future__ import annotations

import unittest
from unittest.mock import patch

from ragrails.interfaces.server.pipeline.schemas import PipelineIngestRequest, PipelineQueryRequest
from ragrails.interfaces.server.pipeline.services import ingest_pipeline, query_pipeline
from ragrails.interfaces.sdk import RagRails
from ragrails.types import ChunkResult, EmbedResult, IngestPipelineResult, RetrieveResult, StoreResult


class ServerPipelineServiceTests(unittest.TestCase):
    def test_ingest_pipeline_calls_sdk(self) -> None:
        chunk = ChunkResult(inputs=1, chunks=1, items=[], failed=0, errors=[])
        embed = EmbedResult(inputs=1, embedded=1, items=[], failed=0, errors=[])
        store = StoreResult(inputs=1, stored=1, items=[], failed=0, provider="qdrant", collection="docs", errors=[])
        expected = IngestPipelineResult(sources=1, chunks=1, embedded=1, stored=1, source_results={}, chunk_result=chunk, embed_result=embed, store_result=store, failed=0, errors=[])

        with patch.object(RagRails, "ingest", return_value=expected) as ingest:
            result = ingest_pipeline(PipelineIngestRequest(markdown="hello", storage={"collection": "docs"}))

        ingest.assert_called_once()
        self.assertEqual(ingest.call_args.kwargs["markdown"], "hello")
        self.assertEqual(result["stored"], 1)

    def test_query_pipeline_calls_sdk(self) -> None:
        expected = RetrieveResult(query="auth", search_query="auth", retrieved=0, items=[], failed=0, errors=[])

        with patch.object(RagRails, "query", return_value=expected) as query:
            result = query_pipeline(PipelineQueryRequest(query="auth", retrieval={"collection": "docs"}))

        query.assert_called_once_with("auth", embedding=None, retrieval={"collection": "docs"})
        self.assertEqual(result["query"], "auth")


if __name__ == "__main__":
    unittest.main()
