"""REST schemas for retrieval."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class RetrieveRequest(BaseModel):
    query: str
    vector_db: Literal["qdrant", "pinecone", "weaviate"] = "qdrant"
    collection: str | None = None
    url: str | None = None
    top_k: int = 10
    embedder: str = "voyage"
    model: str = "voyage-3"
    rerank: bool = False
    reranker: str = "voyage"
    reranker_model: str = "rerank-2-lite"
    rerank_top_k: int = 5


class RetrievedChunkResponse(BaseModel):
    id: str
    score: float
    text: str
    metadata: dict[str, Any]
    rerank_score: float | None = None


class RetrieveResponse(BaseModel):
    query: str
    results: list[RetrievedChunkResponse]
