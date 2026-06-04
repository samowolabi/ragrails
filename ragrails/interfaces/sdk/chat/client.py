"""SDK methods for RAG chat."""

from __future__ import annotations

from ragrails.interfaces.sdk.chat.config import (
    ChatRetrievalQualityConfig,
    HistoryCompactionConfig,
    IntentRoutingConfig,
    QueryRewriteConfig,
)
from ragrails.interfaces.sdk.chat.history import compact_history as compact_chat_history
from ragrails.interfaces.sdk.shared import missing_extra
from ragrails.types import ChatResult


class ChatMixin:
    def llm(
        self,
        *,
        provider: str = "",
        model: str,
        max_tokens: int = 1024,
    ):
        """Create an LLM provider object."""
        self._validate_llm_args(provider=provider, model=model, max_tokens=max_tokens)

        try:
            from ragrails.models.llm.config import LLMConfig, create_llm

            return create_llm(LLMConfig(provider=provider, model=model, max_tokens=max_tokens))
        except ImportError as exc:
            raise missing_extra("Chat", provider or "llm", exc)

    def chat(
        self,
        query: str,
        *,
        llm,
        embedder,
        vector_db: str = "qdrant",
        collection: str | None = None,
        url: str | None = None,
        options: dict | None = None,
        reranker=None,
        history: list[dict] | None = None,
        history_compaction: HistoryCompactionConfig | None = None,
        query_rewrite: QueryRewriteConfig | None = None,
        intent_routing: IntentRoutingConfig | None = None,
        retrieval_quality: ChatRetrievalQualityConfig | None = None,
        persona: str = "",
        retrieval_config=None,
    ) -> ChatResult:
        """Run one stateless chat turn and compact explicit history when needed."""
        history_compaction = history_compaction or HistoryCompactionConfig()
        query_rewrite = query_rewrite or QueryRewriteConfig()
        intent_routing = intent_routing or IntentRoutingConfig()
        retrieval_quality = retrieval_quality or ChatRetrievalQualityConfig()
        self._validate_chat_args(
            query=query,
            llm=llm,
            embedder=embedder,
            options=options,
            history=history,
            history_compaction=history_compaction,
            query_rewrite=query_rewrite,
            intent_routing=intent_routing,
            retrieval_quality=retrieval_quality,
        )

        try:
            from ragrails.core.stg_06_chat import ChatConfig, run_chat
            from ragrails.core.stg_05_retriever import RetrieverConfig
            from ragrails.core.stg_06_chat.quality import RetrievalQualityConfig
            from ragrails.models.vector_db.registry import create_vector_store

            store = create_vector_store(
                provider=vector_db,
                url=url,
                collection=collection,
                **(options or {}),
            )
            result = run_chat(
                query=query,
                llm=llm,
                embedder=embedder,
                store=store,
                reranker=reranker,
                rewrite_llm=query_rewrite.llm,
                chat_config=ChatConfig(
                    persona=persona,
                    use_intent_routing=intent_routing.enabled,
                    retrieval_quality=RetrievalQualityConfig(
                        min_retrieval_score=retrieval_quality.min_retrieval_score,
                        min_rerank_score=retrieval_quality.min_rerank_score,
                        low_confidence_mode=retrieval_quality.low_confidence_mode,
                        max_context_chunks=retrieval_quality.max_context_chunks,
                    ),
                ),
                retrieval_config=retrieval_config or RetrieverConfig(use_query_rewrite=query_rewrite.enabled),
                rewrite_context=persona,
                session_context=query_rewrite.session_context,
                history=list(history or []),
            )
        except ImportError as exc:
            raise missing_extra("Chat", vector_db, exc)

        compacted_history, compacted = compact_chat_history(
            result["history"],
            llm=llm,
            history_limit=history_compaction.history_limit,
            keep_recent=history_compaction.keep_recent,
            enabled=history_compaction.enabled,
        )
        return ChatResult(
            answer=result["answer"],
            sources=result["sources"],
            history=compacted_history,
            retrieval=result["retrieval"],
            llm=result["llm"],
            errors=result["errors"],
            retrieval_quality=result.get("retrieval_quality", {"status": "not_evaluated"}),
            answer_confidence=result.get("answer_confidence", {"level": "unknown", "reason": "missing"}),
            compacted=compacted,
            intent=result.get("intent", "rag"),
        )

    @staticmethod
    def _validate_chat_args(
        *,
        query: str,
        llm,
        embedder,
        options: dict | None,
        history: list[dict] | None,
        history_compaction: HistoryCompactionConfig,
        query_rewrite: QueryRewriteConfig,
        intent_routing: IntentRoutingConfig,
        retrieval_quality: ChatRetrievalQualityConfig,
    ) -> None:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if not hasattr(llm, "complete") or not callable(llm.complete):
            raise TypeError("llm must be an LLM object")
        if (
            not hasattr(embedder, "encode")
            or not callable(embedder.encode)
            or not hasattr(embedder, "vector_size")
        ):
            raise TypeError("embedder must be an embedding model object")
        if options is not None and not isinstance(options, dict):
            raise TypeError("options must be a dictionary")
        if history is not None and not isinstance(history, list):
            raise TypeError("history must be a list of messages")
        if not isinstance(history_compaction, HistoryCompactionConfig):
            raise TypeError("history_compaction must be a HistoryCompactionConfig")
        if not isinstance(query_rewrite, QueryRewriteConfig):
            raise TypeError("query_rewrite must be a QueryRewriteConfig")
        if not isinstance(intent_routing, IntentRoutingConfig):
            raise TypeError("intent_routing must be an IntentRoutingConfig")
        if not isinstance(retrieval_quality, ChatRetrievalQualityConfig):
            raise TypeError("retrieval_quality must be a ChatRetrievalQualityConfig")
        if not isinstance(history_compaction.enabled, bool):
            raise TypeError("history_compaction.enabled must be a boolean")
        if history_compaction.history_limit is not None and (
            isinstance(history_compaction.history_limit, bool)
            or not isinstance(history_compaction.history_limit, int)
            or history_compaction.history_limit < 1
        ):
            raise ValueError("history_compaction.history_limit must be greater than 0 or None")
        if (
            isinstance(history_compaction.keep_recent, bool)
            or not isinstance(history_compaction.keep_recent, int)
            or history_compaction.keep_recent < 1
        ):
            raise ValueError("history_compaction.keep_recent must be greater than 0")
        if (
            history_compaction.history_limit is not None
            and history_compaction.keep_recent >= history_compaction.history_limit
        ):
            raise ValueError("history_compaction.keep_recent must be smaller than history_compaction.history_limit")
        if not isinstance(query_rewrite.enabled, bool):
            raise TypeError("query_rewrite.enabled must be a boolean")
        if not isinstance(query_rewrite.session_context, str):
            raise TypeError("query_rewrite.session_context must be a string")
        if query_rewrite.llm is not None and (
            not hasattr(query_rewrite.llm, "complete") or not callable(query_rewrite.llm.complete)
        ):
            raise TypeError("query_rewrite.llm must be an LLM object")
        if not isinstance(intent_routing.enabled, bool):
            raise TypeError("intent_routing.enabled must be a boolean")
        if (
            isinstance(retrieval_quality.min_retrieval_score, bool)
            or not isinstance(retrieval_quality.min_retrieval_score, (int, float))
        ):
            raise TypeError("retrieval_quality.min_retrieval_score must be a number")
        if (
            isinstance(retrieval_quality.min_rerank_score, bool)
            or not isinstance(retrieval_quality.min_rerank_score, (int, float))
        ):
            raise TypeError("retrieval_quality.min_rerank_score must be a number")
        if not isinstance(retrieval_quality.low_confidence_mode, str):
            raise TypeError("retrieval_quality.low_confidence_mode must be a string")
        if retrieval_quality.max_context_chunks is not None and (
            isinstance(retrieval_quality.max_context_chunks, bool)
            or not isinstance(retrieval_quality.max_context_chunks, int)
            or retrieval_quality.max_context_chunks < 1
        ):
            raise ValueError("retrieval_quality.max_context_chunks must be greater than 0 or None")

    @staticmethod
    def _validate_llm_args(*, provider: str, model: str, max_tokens: int) -> None:
        if provider is not None and not isinstance(provider, str):
            raise TypeError("provider must be a string")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("model is required")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1:
            raise ValueError("max_tokens must be greater than 0")
