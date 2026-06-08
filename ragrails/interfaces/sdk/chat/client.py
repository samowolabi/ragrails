"""SDK methods for RAG chat."""

from __future__ import annotations

from dataclasses import asdict, replace

from ragrails.interfaces.sdk.chat.config import (
    ChatRetrievalQualityConfig,
    HistoryCompactionConfig,
    IntentRoutingConfig,
    QueryRewriteConfig,
)
from ragrails.interfaces.sdk.events import stream_event
from ragrails.interfaces.sdk.chat.history import compact_history as compact_chat_history
from ragrails.interfaces.sdk.shared import configured, configured_object, merge_config, missing_extra, vector_store_config
from ragrails.types import ChatResult


class ChatMixin:
    def llm(
        self,
        *,
        provider: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
    ):
        """Create an LLM provider object."""
        config = merge_config(configured(self, "llm"), {
            "provider": provider,
            "model": model,
            "max_tokens": max_tokens,
        })
        provider = config.get("provider", "")
        model = config.get("model")
        max_tokens = config.get("max_tokens", 1024)
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
        llm=None,
        embedder=None,
        vector_db: str | None = None,
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
        if llm is None:
            llm = configured_object(self, "llm", lambda _: self.llm())
        if embedder is None and hasattr(self, "embedder"):
            embedder = self.embedder(input_type="query")
        vector_db, collection, url, options = vector_store_config(
            self,
            vector_db=vector_db,
            collection=collection,
            url=url,
            options=options,
        )
        if reranker is None:
            reranker = configured_object(self, "reranker", lambda _: self.reranker())
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
            from ragrails.core.stg_06_chat import ChatConfig, QueryRewriteConfig as CoreQueryRewriteConfig, run_chat
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
                retrieval_config=retrieval_config or RetrieverConfig(),
                query_rewrite=CoreQueryRewriteConfig(
                    enabled=query_rewrite.enabled,
                    llm=query_rewrite.llm,
                    context=persona,
                    session_context=query_rewrite.session_context,
                ),
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

    def chat_stream(
        self,
        query: str,
        *,
        llm=None,
        embedder=None,
        vector_db: str | None = None,
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
    ):
        """Yield live RAG chat events and finish with the final ChatResult."""
        sequence = 0

        def event(event_type: str, *, stage: str, message: str = "", data: dict | None = None) -> dict:
            nonlocal sequence
            sequence += 1
            return stream_event(event_type, stage=stage, message=message, data=data, sequence=sequence)

        yield event("progress", stage="chat", message="Chat started", data={"query": query})

        if llm is None:
            llm = configured_object(self, "llm", lambda _: self.llm())
        if embedder is None and hasattr(self, "embedder"):
            embedder = self.embedder(input_type="query")
        vector_db, collection, url, options = vector_store_config(
            self,
            vector_db=vector_db,
            collection=collection,
            url=url,
            options=options,
        )
        if reranker is None:
            reranker = configured_object(self, "reranker", lambda _: self.reranker())
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
            from ragrails.core.stg_05_retriever import RetrieverConfig, run_retrieval
            from ragrails.core.stg_06_chat import ChatConfig
            from ragrails.core.stg_06_chat.chat import _append_history, _failure, _response
            from ragrails.core.stg_06_chat.confidence import build_answer_confidence
            from ragrails.core.stg_06_chat.context import build_context, extract_sources, validate_citations
            from ragrails.core.stg_06_chat.intent import RAG_INTENT, detect_intent, should_bypass_retrieval
            from ragrails.core.stg_06_chat.prompts import build_system_prompt, build_user_prompt
            from ragrails.core.stg_06_chat.quality import RETURN_NO_ANSWER, RetrievalQualityConfig, filter_by_quality
            from ragrails.models.vector_db.registry import create_vector_store
        except ImportError as exc:
            raise missing_extra("Chat", vector_db, exc)

        core_chat_config = ChatConfig(
            persona=persona,
            use_intent_routing=intent_routing.enabled,
            retrieval_quality=RetrievalQualityConfig(
                min_retrieval_score=retrieval_quality.min_retrieval_score,
                min_rerank_score=retrieval_quality.min_rerank_score,
                low_confidence_mode=retrieval_quality.low_confidence_mode,
                max_context_chunks=retrieval_quality.max_context_chunks,
            ),
        )

        intent = detect_intent(query) if intent_routing.enabled else RAG_INTENT
        yield event("progress", stage="intent", message="Intent detected", data={"intent": intent})

        retrieval = {"retrieved": 0, "failed": 0, "outputs": [], "errors": []}
        sources: list[dict] = []
        quality = {"status": "skipped", "reason": "intent_bypass"} if should_bypass_retrieval(intent) else {"status": "not_evaluated"}
        errors: list[dict] = []
        user_prompt = query

        if not should_bypass_retrieval(intent):
            yield event("progress", stage="retrieval", message="Retrieval started")
            store = create_vector_store(
                provider=vector_db,
                url=url,
                collection=collection,
                **(options or {}),
            )
            retrieval = run_retrieval(
                query=query,
                model=embedder,
                store=store,
                rewrite_llm=query_rewrite.llm or llm,
                reranker=reranker,
                config=replace(retrieval_config or RetrieverConfig(), use_query_rewrite=query_rewrite.enabled),
                rewrite_context=persona,
                session_context=query_rewrite.session_context,
            )
            yield event(
                "progress",
                stage="retrieval",
                message="Retrieval complete",
                data={
                    "retrieved": retrieval.get("retrieved", 0),
                    "failed": retrieval.get("failed", 0),
                    "search_query": retrieval.get("search_query", query),
                },
            )
            if retrieval.get("errors"):
                result = _response(answer="", history=history, retrieval=retrieval, errors=retrieval["errors"], intent=intent)
                final = self._final_chat_result(result, llm=llm, history_compaction=history_compaction)
                yield event("final", stage="complete", message="Chat complete", data=asdict(final))
                return

            selected, quality = filter_by_quality(retrieval["outputs"], core_chat_config.retrieval_quality)
            yield event("progress", stage="quality", message="Retrieval quality evaluated", data=quality)
            if quality["status"] == "low_confidence" and quality["mode"] == RETURN_NO_ANSWER:
                result = _response(
                    answer="",
                    history=history,
                    retrieval=retrieval,
                    errors=[_failure(stage="quality", error="retrieval quality below configured threshold")],
                    intent=intent,
                    retrieval_quality=quality,
                )
                final = self._final_chat_result(result, llm=llm, history_compaction=history_compaction)
                yield event("final", stage="complete", message="Chat complete", data=asdict(final))
                return

            sources = extract_sources(selected)
            context = build_context(selected)
            user_prompt = build_user_prompt(query, context)

        system_prompt = build_system_prompt(core_chat_config)
        answer = ""
        try:
            yield event("progress", stage="generation", message="Generation started")
            for token in llm.stream(system=system_prompt, user=user_prompt, history=list(history or [])):
                answer += token
                yield event("token", stage="generation", data={"text": token})
        except Exception as exc:
            result = _response(
                answer="",
                history=history,
                retrieval=retrieval,
                sources=sources,
                errors=[_failure(stage="generate", error=str(exc), is_retryable=True)],
                intent=intent,
                retrieval_quality=quality,
            )
            final = self._final_chat_result(result, llm=llm, history_compaction=history_compaction)
            yield event("error", stage="generation", message=str(exc), data={"error": str(exc)})
            yield event("final", stage="complete", message="Chat complete", data=asdict(final))
            return

        answer = validate_citations(answer, sources) if sources else answer
        updated_history = _append_history(history, query=query, answer=answer)
        result = _response(
            answer=answer,
            history=updated_history,
            retrieval=retrieval,
            sources=sources,
            llm={"provider": getattr(llm, "provider", ""), "model": getattr(llm, "model", "")},
            errors=errors,
            intent=intent,
            retrieval_quality=quality,
            answer_confidence=build_answer_confidence(
                retrieval_quality=quality,
                sources=sources,
                intent=intent,
                errors=errors,
            ),
        )
        final = self._final_chat_result(result, llm=llm, history_compaction=history_compaction)
        yield event("final", stage="complete", message="Chat complete", data=asdict(final))

    @staticmethod
    def _final_chat_result(result: dict, *, llm, history_compaction: HistoryCompactionConfig) -> ChatResult:
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
