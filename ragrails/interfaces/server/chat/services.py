"""REST services for chat."""

from __future__ import annotations

from typing import Any

from ragrails.core.stg_05_retriever import RetrieverConfig
from ragrails.interfaces.sdk import RagRails
from ragrails.interfaces.sdk.chat import (
    ChatRetrievalQualityConfig,
    HistoryCompactionConfig,
    IntentRoutingConfig,
    QueryRewriteConfig,
)
from ragrails.interfaces.server.common import model_data, result_data

from .schemas import ChatRequest


def run_chat(request: ChatRequest) -> dict[str, Any]:
    data = model_data(request)
    query = data.pop("query")
    llm_provider = data.pop("llm_provider")
    llm_model = data.pop("llm_model")
    max_tokens = data.pop("max_tokens")
    embedder_provider = data.pop("embedder_provider")
    embedder_model = data.pop("embedder_model")
    embedder_options = data.pop("embedder_options")
    rerank = data.pop("rerank")
    reranker_provider = data.pop("reranker")
    reranker_model = data.pop("reranker_model")
    reranker_options = data.pop("reranker_options")
    rerank_top_k = data.pop("rerank_top_k")
    history_compaction = data.pop("history_compaction") or {}
    query_rewrite = data.pop("query_rewrite") or {}
    intent_routing = data.pop("intent_routing") or {}
    retrieval_quality = data.pop("retrieval_quality") or {}

    rag = RagRails()
    llm = rag.llm(provider=llm_provider, model=llm_model, max_tokens=max_tokens)
    embedder = rag.embedder(provider=embedder_provider, model=embedder_model, input_type="query", options=embedder_options)
    reranker = rag.reranker(provider=reranker_provider, model=reranker_model, options=reranker_options) if rerank else None
    retrieval_config = RetrieverConfig(use_rerank=rerank, rerank_top_k=rerank_top_k)

    return result_data(
        rag.chat(
            query,
            llm=llm,
            embedder=embedder,
            reranker=reranker,
            history_compaction=HistoryCompactionConfig(**history_compaction),
            query_rewrite=QueryRewriteConfig(**query_rewrite),
            intent_routing=IntentRoutingConfig(**intent_routing),
            retrieval_quality=ChatRetrievalQualityConfig(**retrieval_quality),
            retrieval_config=retrieval_config,
            **data,
        )
    )
