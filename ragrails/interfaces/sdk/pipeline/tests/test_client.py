from __future__ import annotations

import unittest

from ragrails.interfaces.sdk.pipeline.client import PipelineMixin
from ragrails.types import ApiIngestResult, ChunkResult, EmbedResult, ParseResult, RetrieveResult, ScrapeResult, StoreResult


class FakeEmbedder:
    vector_size = 1

    def encode(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _ in texts]


class FakeReranker:
    def rerank(self, query: str, texts: list[str]) -> list[float]:
        return [1.0 for _ in texts]


class PipelineSDK(PipelineMixin):
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.created_embedder = FakeEmbedder()
        self.created_reranker = FakeReranker()

    def parse(self, **kwargs):
        self.calls.append(("parse", kwargs))
        return ParseResult(documents=1, failed=0, outputs=[{"text": "Doc text", "source": "doc.md", "metadata": {}}], errors=[])

    def scrape(self, **kwargs):
        self.calls.append(("scrape", kwargs))
        return ScrapeResult(pages=1, failed=0, outputs=[{"text": "URL text", "source": "https://example.com", "metadata": {}}], errors=[])

    def fetch(self, **kwargs):
        self.calls.append(("fetch", kwargs))
        return ApiIngestResult(documents=1, failed=0, outputs=[{"text": "API text", "source": "api", "metadata": {}}], errors=[])

    def chunk(self, **kwargs):
        self.calls.append(("chunk", kwargs))
        return ChunkResult(
            inputs=len(kwargs["markdown"]),
            chunks=1,
            items=[{"id": "chunk-1", "text": "Chunk text", "source": "doc.md", "metadata": {}}],
            failed=0,
            errors=[],
        )

    def embedder(self, **kwargs):
        self.calls.append(("embedder", kwargs))
        return self.created_embedder

    def embed(self, **kwargs):
        self.calls.append(("embed", kwargs))
        return EmbedResult(
            inputs=1,
            embedded=1,
            items=[{"id": "chunk-1", "text": "Chunk text", "embedding": [1.0], "metadata": {}}],
            failed=0,
            errors=[],
        )

    def store(self, **kwargs):
        self.calls.append(("store", kwargs))
        return StoreResult(
            inputs=1,
            stored=1,
            items=[{"id": "chunk-1"}],
            failed=0,
            provider=kwargs.get("vector_db", "qdrant"),
            collection=kwargs.get("collection", ""),
            errors=[],
        )

    def reranker(self, **kwargs):
        self.calls.append(("reranker", kwargs))
        return self.created_reranker

    def retrieve(self, query, **kwargs):
        self.calls.append(("retrieve", {"query": query, **kwargs}))
        return RetrieveResult(query=query, search_query=query, retrieved=0, items=[], failed=0, errors=[])


class PipelineSDKTests(unittest.TestCase):
    def test_ingest_runs_markdown_pipeline(self) -> None:
        sdk = PipelineSDK()

        result = sdk.ingest(
            markdown="Hello",
            chunking={"chunk_size": 500, "chunk_overlap": 50},
            embedding={"provider": "voyage", "model": "voyage-3", "batch_size": 16},
            storage={"vector_db": "qdrant", "collection": "docs"},
        )

        self.assertEqual(result.sources, 1)
        self.assertEqual(result.chunks, 1)
        self.assertEqual(result.embedded, 1)
        self.assertEqual(result.stored, 1)
        self.assertEqual(result.failed, 0)
        self.assertEqual([name for name, _ in sdk.calls], ["chunk", "embedder", "embed", "store"])
        self.assertEqual(sdk.calls[0][1]["chunk_size"], 500)
        self.assertEqual(sdk.calls[1][1], {"input_type": "document", "provider": "voyage", "model": "voyage-3"})
        self.assertEqual(sdk.calls[2][1]["batch_size"], 16)
        self.assertEqual(sdk.calls[3][1]["collection"], "docs")

    def test_ingest_runs_all_source_types(self) -> None:
        sdk = PipelineSDK()

        result = sdk.ingest(
            docs=["guide.md"],
            urls="https://example.com",
            api="https://api.example.com/posts",
            ingestion={
                "docs": {"frontmatter": True},
                "urls": {"mode": "full"},
                "api": {"max_pages": 2},
            },
        )

        self.assertEqual(result.sources, 3)
        self.assertEqual(set(result.source_results), {"docs", "urls", "api"})
        self.assertEqual(sdk.calls[0], ("parse", {"files": ["guide.md"], "frontmatter": True}))
        self.assertEqual(sdk.calls[1], ("scrape", {"url": "https://example.com", "mode": "full"}))
        self.assertEqual(sdk.calls[2], ("fetch", {"url": "https://api.example.com/posts", "max_pages": 2}))
        self.assertEqual(len(sdk.calls[3][1]["markdown"]), 3)

    def test_ingest_can_run_source_types_in_parallel(self) -> None:
        sdk = PipelineSDK()

        result = sdk.ingest(
            docs=["guide.md"],
            urls="https://example.com",
            api="https://api.example.com/posts",
            markdown="Manual text",
            concurrency="parallel",
        )

        self.assertEqual(result.sources, 4)
        self.assertEqual(set(result.source_results), {"docs", "urls", "api", "markdown"})
        chunk_call = next(kwargs for name, kwargs in sdk.calls if name == "chunk")
        self.assertEqual(
            [item["text"] for item in chunk_call["markdown"]],
            ["Doc text", "URL text", "API text", "Manual text"],
        )

    def test_ingest_accepts_stage_argument_dicts(self) -> None:
        sdk = PipelineSDK()

        sdk.ingest(
            docs={"folder": "docs"},
            urls={"url": "https://example.com/docs", "max_depth": 1},
            api={"apis": ["https://api.example.com/posts"]},
        )

        self.assertEqual(sdk.calls[0], ("parse", {"folder": "docs"}))
        self.assertEqual(sdk.calls[1], ("scrape", {"url": "https://example.com/docs", "max_depth": 1}))
        self.assertEqual(sdk.calls[2], ("fetch", {"apis": ["https://api.example.com/posts"]}))

    def test_ingest_rejects_no_source(self) -> None:
        with self.assertRaisesRegex(ValueError, "Provide at least one source"):
            PipelineSDK().ingest()

    def test_ingest_rejects_invalid_config(self) -> None:
        with self.assertRaisesRegex(TypeError, "storage must be a dictionary"):
            PipelineSDK().ingest(markdown="Hello", storage=["bad"])

        with self.assertRaisesRegex(TypeError, "ingestion\\['docs'\\] must be a dictionary"):
            PipelineSDK().ingest(docs=["guide.md"], ingestion={"docs": ["bad"]})

        with self.assertRaisesRegex(ValueError, "concurrency must be 'serial' or 'parallel'"):
            PipelineSDK().ingest(markdown="Hello", concurrency="bad")

    def test_query_creates_embedder_and_retrieves(self) -> None:
        sdk = PipelineSDK()

        result = sdk.query(
            "What is auth?",
            embedding={"provider": "voyage", "model": "voyage-3"},
            retrieval={"vector_db": "qdrant", "collection": "docs", "top_k": 5},
        )

        self.assertEqual(result.query, "What is auth?")
        self.assertEqual([name for name, _ in sdk.calls], ["embedder", "retrieve"])
        self.assertEqual(sdk.calls[0][1], {"input_type": "query", "provider": "voyage", "model": "voyage-3"})
        self.assertIs(sdk.calls[1][1]["embedder"], sdk.created_embedder)
        self.assertEqual(sdk.calls[1][1]["collection"], "docs")
        self.assertEqual(sdk.calls[1][1]["top_k"], 5)

    def test_query_maps_rewrite_and_rerank_config(self) -> None:
        sdk = PipelineSDK()
        rewrite_llm = object()
        explicit_reranker = FakeReranker()

        sdk.query(
            "What is auth?",
            retrieval={
                "query_rewrite": {
                    "enabled": True,
                    "llm": rewrite_llm,
                    "context": "Docs",
                    "session_context": "Session",
                },
                "rerank": {"enabled": True, "reranker": explicit_reranker, "top_k": 3},
            },
        )

        retrieve_call = sdk.calls[-1][1]
        self.assertTrue(retrieve_call["use_query_rewrite"])
        self.assertIs(retrieve_call["rewrite_llm"], rewrite_llm)
        self.assertEqual(retrieve_call["rewrite_context"], "Docs")
        self.assertEqual(retrieve_call["session_context"], "Session")
        self.assertTrue(retrieve_call["use_rerank"])
        self.assertIs(retrieve_call["reranker"], explicit_reranker)
        self.assertEqual(retrieve_call["rerank_top_k"], 3)

    def test_query_can_create_reranker_from_config(self) -> None:
        sdk = PipelineSDK()

        sdk.query(
            "What is auth?",
            retrieval={"rerank": {"enabled": True, "provider": "voyage", "model": "rerank-2-lite"}},
        )

        self.assertEqual(sdk.calls[0], ("reranker", {"provider": "voyage", "model": "rerank-2-lite"}))
        self.assertIs(sdk.calls[-1][1]["reranker"], sdk.created_reranker)

    def test_query_rejects_invalid_config(self) -> None:
        with self.assertRaisesRegex(TypeError, "embedding must be a dictionary"):
            PipelineSDK().query("auth", embedding=["bad"])

        with self.assertRaisesRegex(TypeError, "query_rewrite must be a dictionary"):
            PipelineSDK().query("auth", retrieval={"query_rewrite": ["bad"]})


if __name__ == "__main__":
    unittest.main()
