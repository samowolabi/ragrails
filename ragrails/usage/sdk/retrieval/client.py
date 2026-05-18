"""SDK methods for retrieval."""

from __future__ import annotations

from typing import Literal

from ragrails.types import RetrievedChunk, RetrieveResult
from ragrails.usage.sdk.shared import missing_extra
from ragrails.usage.sdk.storing.client import validate_vector_store_collection


class RetrievalMixin:
    def retrieve(
        self,
        query: str,
        *,
        vector_db: Literal["qdrant", "pinecone", "weaviate"] = "qdrant",
        collection: str | None = None,
        url: str | None = None,
        top_k: int = 10,
        embedder: str = "voyage",
        model: str = "voyage-3",
        rerank: bool = False,
        reranker: str = "voyage",
        reranker_model: str = "rerank-2-lite",
        rerank_top_k: int = 5,
    ) -> RetrieveResult:
        """Retrieve the most relevant chunks for a query."""
        self._validate_retrieve_args(
            query=query,
            vector_db=vector_db,
            collection=collection,
            top_k=top_k,
            embedder=embedder,
            model=model,
            reranker=reranker,
            reranker_model=reranker_model,
            rerank_top_k=rerank_top_k,
        )

        try:
            from ragrails.models.embedder.config import EmbedderConfig
            from ragrails.models.embedder.config import create_embedder
            from ragrails.models.reranker.config import RerankerConfig
            from ragrails.models.reranker.config import create_reranker
            from ragrails.models.vector_db.registry import create_vector_store
            from ragrails.pipeline.stg_04_retriever.retriever import rerank as _rerank
            from ragrails.pipeline.stg_04_retriever.retriever import retrieve as _retrieve
        except ImportError as exc:
            raise missing_extra("Retrieval", f"{embedder},{vector_db}", exc)

        embedding_model = create_embedder(
            EmbedderConfig(provider=embedder, model=model),
            input_type="query",
        )
        vector_store = create_vector_store(
            provider=vector_db,
            url=url,
            collection=collection,
        )
        results = _retrieve(
            query=query,
            model=embedding_model,
            store=vector_store,
            top_k=top_k,
        )

        if rerank:
            rerank_model = create_reranker(RerankerConfig(provider=reranker, model=reranker_model))
            results = _rerank(query=query, results=results, model=rerank_model, top_k=rerank_top_k)

        return RetrieveResult(
            query=query,
            results=[
                RetrievedChunk(
                    id=item.id,
                    score=item.score,
                    text=item.text,
                    metadata=item.metadata,
                    rerank_score=item.rerank_score,
                )
                for item in results
            ],
        )

    @staticmethod
    def _validate_retrieve_args(
        *,
        query: str,
        vector_db: str,
        collection: str | None,
        top_k: int,
        embedder: str,
        model: str,
        reranker: str,
        reranker_model: str,
        rerank_top_k: int,
    ) -> None:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        validate_vector_store_collection(vector_db=vector_db, collection=collection)
        if top_k < 1:
            raise ValueError("top_k must be greater than 0")
        if rerank_top_k < 1:
            raise ValueError("rerank_top_k must be greater than 0")
        if not embedder:
            raise ValueError("embedder is required")
        if not model:
            raise ValueError("model is required")
        if not reranker:
            raise ValueError("reranker is required")
        if not reranker_model:
            raise ValueError("reranker_model is required")
