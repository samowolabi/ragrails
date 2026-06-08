"""REST schemas for retrieval."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class RetrieveRequest(BaseModel):
    query: str
    provider: str = "voyage"
    model: str = "voyage-3"
    embedder_options: dict[str, Any] | None = None
    vector_db: Literal["qdrant", "qdrant_cloud", "pinecone", "weaviate"] = "qdrant"
    collection: str | None = None
    url: str | None = None
    options: dict[str, Any] | None = None
    top_k: int = 10
    use_query_rewrite: bool = False
    rewrite_context: str = ""
    session_context: str = ""
    use_rerank: bool = False
    reranker: str = "voyage"
    reranker_model: str = "rerank-2-lite"
    reranker_options: dict[str, Any] | None = None
    rerank_top_k: int = 5


class RetrievedChunkResponse(BaseModel):
    id: str
    chunk_id: str
    score: float
    text: str
    metadata: dict[str, Any]
    rerank_score: float | None = None


class RetrieveResponse(BaseModel):
    query: str
    search_query: str
    retrieved: int
    items: list[RetrievedChunkResponse]
    failed: int
    errors: list[dict[str, Any]]
