"""REST schemas for chat."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class QueryRewriteRequest(BaseModel):
    enabled: bool = False
    session_context: str = ""


class HistoryCompactionRequest(BaseModel):
    enabled: bool = True
    history_limit: int | None = 15
    keep_recent: int = 5


class IntentRoutingRequest(BaseModel):
    enabled: bool = True


class ChatRetrievalQualityRequest(BaseModel):
    min_retrieval_score: float = 0.0
    min_rerank_score: float = 0.0
    low_confidence_mode: Literal["answer_with_caution", "ask_clarifying_question", "refuse_grounded_answer", "return_no_answer"] = "answer_with_caution"
    max_context_chunks: int | None = None


class ChatRequest(BaseModel):
    query: str
    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-mini"
    max_tokens: int = 1024
    embedder_provider: str = "voyage"
    embedder_model: str = "voyage-3"
    embedder_options: dict[str, Any] | None = None
    vector_db: Literal["qdrant", "pinecone", "weaviate"] = "qdrant"
    collection: str | None = None
    url: str | None = None
    options: dict[str, Any] | None = None
    rerank: bool = False
    reranker: str = "voyage"
    reranker_model: str = "rerank-2-lite"
    reranker_options: dict[str, Any] | None = None
    rerank_top_k: int = 5
    history: list[dict[str, Any]] | None = None
    history_compaction: HistoryCompactionRequest | None = None
    query_rewrite: QueryRewriteRequest | None = None
    intent_routing: IntentRoutingRequest | None = None
    retrieval_quality: ChatRetrievalQualityRequest | None = None
    persona: str = ""


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict[str, Any]]
    history: list[dict[str, Any]]
    retrieval: dict[str, Any]
    llm: dict[str, Any]
    errors: list[dict[str, Any]]
    retrieval_quality: dict[str, Any]
    answer_confidence: dict[str, Any]
    compacted: bool = False
    intent: str = "rag"
