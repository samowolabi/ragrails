"""SDK pipeline convenience methods."""

from __future__ import annotations

from typing import Any

from ragrails.types import IngestPipelineResult, RetrieveResult


class PipelineMixin:
    def ingest(
        self,
        *,
        docs: str | list[str | dict] | dict[str, Any] | None = None,
        urls: str | list[str | dict] | dict[str, Any] | None = None,
        api: str | list[str | dict] | dict[str, Any] | None = None,
        markdown: str | list[str | dict[str, Any]] | None = None,
        ingestion: dict[str, Any] | None = None,
        chunking: dict[str, Any] | None = None,
        embedding: dict[str, Any] | None = None,
        storage: dict[str, Any] | None = None,
    ) -> IngestPipelineResult:
        """Run source ingestion, chunking, embedding, and vector storage."""
        self._validate_pipeline_config(
            ingestion=ingestion,
            chunking=chunking,
            embedding=embedding,
            storage=storage,
        )
        if all(source is None for source in (docs, urls, api, markdown)):
            raise ValueError("Provide at least one source: docs, urls, api, or markdown")

        source_results: dict[str, object] = {}
        documents: list[dict[str, Any]] = []
        errors: list[dict] = []

        if docs is not None:
            result = self._pipeline_parse(docs, ingestion)
            source_results["docs"] = result
            documents.extend(result.outputs)
            errors.extend(self._tag_pipeline_errors("docs", result.errors))

        if urls is not None:
            result = self._pipeline_scrape(urls, ingestion)
            source_results["urls"] = result
            documents.extend(result.outputs)
            errors.extend(self._tag_pipeline_errors("urls", result.errors))

        if api is not None:
            result = self._pipeline_fetch(api, ingestion)
            source_results["api"] = result
            documents.extend(result.outputs)
            errors.extend(self._tag_pipeline_errors("api", result.errors))

        if markdown is not None:
            markdown_docs = self._pipeline_markdown_documents(markdown)
            source_results["markdown"] = markdown_docs
            documents.extend(markdown_docs)

        if not documents:
            raise ValueError("Ingestion produced no documents to chunk")

        embedding_config = dict(embedding or {})
        embed_batch_size = embedding_config.pop("batch_size", 64)
        chunk_result = self.chunk(markdown=documents, **(chunking or {}))
        embedder = self.embedder(**{"input_type": "document", **embedding_config})
        embed_result = self.embed(
            chunks=chunk_result.items,
            embedder=embedder,
            batch_size=embed_batch_size,
        )
        store_result = self.store(
            embedded_chunks=embed_result.items,
            **(storage or {}),
        )

        errors.extend(self._tag_pipeline_errors("chunking", chunk_result.errors))
        errors.extend(self._tag_pipeline_errors("embedding", embed_result.errors))
        errors.extend(self._tag_pipeline_errors("storage", store_result.errors))

        return IngestPipelineResult(
            sources=len(documents),
            chunks=chunk_result.chunks,
            embedded=embed_result.embedded,
            stored=store_result.stored,
            source_results=source_results,
            chunk_result=chunk_result,
            embed_result=embed_result,
            store_result=store_result,
            failed=(
                self._pipeline_failed(source_results)
                + chunk_result.failed
                + embed_result.failed
                + store_result.failed
            ),
            errors=errors,
        )

    def query(
        self,
        query: str,
        *,
        embedding: dict[str, Any] | None = None,
        retrieval: dict[str, Any] | None = None,
    ) -> RetrieveResult:
        """Run query embedding and vector retrieval."""
        if embedding is not None and not isinstance(embedding, dict):
            raise TypeError("embedding must be a dictionary")
        if retrieval is not None and not isinstance(retrieval, dict):
            raise TypeError("retrieval must be a dictionary")

        embedding_config = {"input_type": "query", **(embedding or {})}
        retrieval_config = dict(retrieval or {})
        query_rewrite = retrieval_config.pop("query_rewrite", None)
        rerank = retrieval_config.pop("rerank", None)

        if query_rewrite is not None:
            if not isinstance(query_rewrite, dict):
                raise TypeError("query_rewrite must be a dictionary")
            enabled = bool(query_rewrite.get("enabled", False))
            retrieval_config["use_query_rewrite"] = enabled
            if "llm" in query_rewrite:
                retrieval_config["rewrite_llm"] = query_rewrite["llm"]
            if "context" in query_rewrite:
                retrieval_config["rewrite_context"] = query_rewrite["context"]
            if "session_context" in query_rewrite:
                retrieval_config["session_context"] = query_rewrite["session_context"]

        if rerank is not None:
            if not isinstance(rerank, dict):
                raise TypeError("rerank must be a dictionary")
            enabled = bool(rerank.get("enabled", False))
            retrieval_config["use_rerank"] = enabled
            if enabled and "reranker" not in rerank:
                reranker_config = {k: v for k, v in rerank.items() if k not in {"enabled", "top_k"}}
                retrieval_config["reranker"] = self.reranker(**reranker_config)
            elif "reranker" in rerank:
                retrieval_config["reranker"] = rerank["reranker"]
            if "top_k" in rerank:
                retrieval_config["rerank_top_k"] = rerank["top_k"]

        embedder = self.embedder(**embedding_config)
        return self.retrieve(query, embedder=embedder, **retrieval_config)

    def _pipeline_parse(self, docs, ingestion: dict[str, Any] | None):
        config = self._stage_config(ingestion, "docs")
        if isinstance(docs, dict):
            config = {**config, **docs}
            return self.parse(**config)
        return self.parse(files=docs, **config)

    def _pipeline_scrape(self, urls, ingestion: dict[str, Any] | None):
        config = self._stage_config(ingestion, "urls")
        if isinstance(urls, dict):
            config = {**config, **urls}
            return self.scrape(**config)
        return self.scrape(url=urls, **config)

    def _pipeline_fetch(self, api, ingestion: dict[str, Any] | None):
        config = self._stage_config(ingestion, "api")
        if isinstance(api, dict):
            config = {**config, **api}
            return self.fetch(**config)
        if isinstance(api, list):
            return self.fetch(apis=api, **config)
        return self.fetch(url=api, **config)

    @staticmethod
    def _stage_config(config: dict[str, Any] | None, stage: str) -> dict[str, Any]:
        if not config:
            return {}
        stage_config = config.get(stage, {})
        if stage_config is None:
            return {}
        if not isinstance(stage_config, dict):
            raise TypeError(f"ingestion['{stage}'] must be a dictionary")
        return dict(stage_config)

    @staticmethod
    def _pipeline_markdown_documents(markdown: str | list[str | dict[str, Any]]) -> list[dict[str, Any]]:
        if isinstance(markdown, str):
            return [{"text": markdown, "source": "markdown", "metadata": {}}]
        return list(markdown)

    @staticmethod
    def _validate_pipeline_config(
        *,
        ingestion: dict[str, Any] | None,
        chunking: dict[str, Any] | None,
        embedding: dict[str, Any] | None,
        storage: dict[str, Any] | None,
    ) -> None:
        for name, value in {
            "ingestion": ingestion,
            "chunking": chunking,
            "embedding": embedding,
            "storage": storage,
        }.items():
            if value is not None and not isinstance(value, dict):
                raise TypeError(f"{name} must be a dictionary")

    @staticmethod
    def _pipeline_failed(source_results: dict[str, object]) -> int:
        return sum(getattr(result, "failed", 0) for result in source_results.values())

    @staticmethod
    def _tag_pipeline_errors(stage: str, errors: list) -> list[dict]:
        tagged = []
        for error in errors:
            if isinstance(error, dict):
                tagged.append({"stage": stage, **error})
            else:
                tagged.append({"stage": stage, "error": str(error)})
        return tagged
