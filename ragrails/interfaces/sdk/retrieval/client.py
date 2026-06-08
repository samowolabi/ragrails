"""SDK methods for retrieval."""

from __future__ import annotations

from typing import Any, Literal

from ragrails.types import RetrievedChunk, RetrieveResult
from ragrails.interfaces.sdk.shared import configured, configured_object, merge_config, missing_extra, vector_store_config
from ragrails.interfaces.sdk.storing.client import validate_vector_store_collection


class RetrievalMixin:
    def reranker(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        options: dict[str, Any] | None = None,
    ):
        """Create a reranker model object."""
        config = merge_config(configured(self, "reranker"), {
            "provider": provider,
            "model": model,
            "options": options,
        })
        config.pop("enabled", None)
        provider = config.get("provider", "voyage")
        model = config.get("model", "rerank-2-lite")
        options = config.get("options")
        self._validate_reranker_args(provider=provider, model=model, options=options)

        try:
            from ragrails.models.reranker.config import RerankerConfig
            from ragrails.models.reranker.config import create_reranker

            return create_reranker(RerankerConfig(provider=provider, model=model, options=options))
        except ImportError as exc:
            raise missing_extra("Reranking", provider, exc)

    def retrieve(
        self,
        query: str,
        *,
        embedder=None,
        vector_db: Literal["qdrant", "qdrant_cloud", "pinecone", "weaviate"] | None = None,
        collection: str | None = None,
        url: str | None = None,
        options: dict[str, Any] | None = None,
        top_k: int = 10,
        use_query_rewrite: bool = False,
        rewrite_llm=None,
        rewrite_context: str = "",
        session_context: str = "",
        use_rerank: bool = False,
        reranker=None,
        rerank_top_k: int = 5,
    ) -> RetrieveResult:
        """Retrieve the most relevant chunks for a query."""
        if embedder is None and hasattr(self, "embedder"):
            embedder = self.embedder(input_type="query")
        vector_db, collection, url, options = vector_store_config(
            self,
            vector_db=vector_db,
            collection=collection,
            url=url,
            options=options,
        )
        if use_query_rewrite and rewrite_llm is None and configured(self, "llm") and hasattr(self, "llm"):
            rewrite_llm = self.llm()
        if use_rerank and reranker is None:
            reranker = configured_object(self, "reranker", lambda _: self.reranker())
        self._validate_retrieve_args(
            query=query,
            embedder=embedder,
            vector_db=vector_db,
            collection=collection,
            options=options,
            top_k=top_k,
            use_query_rewrite=use_query_rewrite,
            rewrite_llm=rewrite_llm,
            use_rerank=use_rerank,
            reranker=reranker,
            rerank_top_k=rerank_top_k,
        )

        try:
            from ragrails.core.stg_05_retriever.config import RetrieverConfig
            from ragrails.core.stg_05_retriever.retriever import run_retrieval
            from ragrails.models.vector_db.registry import create_vector_store

            vector_store = create_vector_store(
                provider=vector_db,
                url=url,
                collection=collection,
                **(options or {}),
            )
            stats = run_retrieval(
                query=query,
                model=embedder,
                store=vector_store,
                rewrite_llm=rewrite_llm,
                reranker=reranker,
                config=RetrieverConfig(
                    top_k=top_k,
                    use_query_rewrite=use_query_rewrite,
                    use_rerank=use_rerank,
                    rerank_top_k=rerank_top_k,
                ),
                rewrite_context=rewrite_context,
                session_context=session_context,
            )
        except ImportError as exc:
            raise missing_extra("Retrieval", vector_db, exc)

        return RetrieveResult(
            query=stats.get("query", query),
            search_query=stats.get("search_query", query),
            retrieved=stats.get("retrieved", 0),
            items=[
                RetrievedChunk(
                    id=item.id,
                    chunk_id=item.chunk_id,
                    score=item.score,
                    text=item.text,
                    metadata=item.metadata,
                    rerank_score=item.rerank_score,
                )
                for item in stats.get("outputs", [])
            ],
            failed=stats.get("failed", 0),
            errors=stats.get("errors", []),
        )

    @staticmethod
    def _validate_retrieve_args(
        *,
        query: str,
        embedder,
        vector_db: str,
        collection: str | None,
        options: dict[str, Any] | None,
        top_k: int,
        use_query_rewrite: bool,
        rewrite_llm,
        use_rerank: bool,
        reranker,
        rerank_top_k: int,
    ) -> None:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if (
            not hasattr(embedder, "encode")
            or not callable(embedder.encode)
            or not hasattr(embedder, "vector_size")
        ):
            raise TypeError("embedder must be an embedding model object")
        validate_vector_store_collection(vector_db=vector_db, collection=collection)
        if options is not None and not isinstance(options, dict):
            raise TypeError("options must be a dictionary")
        if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
            raise ValueError("top_k must be greater than 0")
        if isinstance(rerank_top_k, bool) or not isinstance(rerank_top_k, int) or rerank_top_k < 1:
            raise ValueError("rerank_top_k must be greater than 0")
        if not isinstance(use_query_rewrite, bool):
            raise TypeError("use_query_rewrite must be a boolean")
        if use_query_rewrite and (
            rewrite_llm is None
            or not hasattr(rewrite_llm, "complete")
            or not callable(rewrite_llm.complete)
        ):
            raise TypeError("rewrite_llm must be an LLM object when use_query_rewrite is True")
        if not isinstance(use_rerank, bool):
            raise TypeError("use_rerank must be a boolean")
        if use_rerank and (
            reranker is None
            or not hasattr(reranker, "rerank")
            or not callable(reranker.rerank)
        ):
            raise TypeError("reranker must be a reranker object when use_rerank is True")

    @staticmethod
    def _validate_reranker_args(
        *,
        provider: str,
        model: str,
        options: dict[str, Any] | None,
    ) -> None:
        if not isinstance(provider, str) or not provider.strip():
            raise ValueError("provider is required")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model is required")
        if options is not None and not isinstance(options, dict):
            raise TypeError("options must be a dictionary")
