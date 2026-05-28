"""Core chat orchestration.

This module contains the reusable chat flow. It does not print, read files,
write files, manage sessions, or own transport concerns.
"""

from __future__ import annotations

from ragrails.models.embedder.base import EmbeddingModel
from ragrails.models.llm.base import History, LLMProvider
from ragrails.models.reranker.base import Reranker
from ragrails.models.vector_db.base import VectorStore
from ragrails.core.stg_05_retriever import RetrieverConfig, run_retrieval

from .config import ChatConfig
from .context import build_context, extract_sources, validate_citations
from .intent import RAG_INTENT, detect_intent, should_bypass_retrieval
from .prompts import build_system_prompt, build_user_prompt
from .quality import (
    ASK_CLARIFYING_QUESTION,
    REFUSE_GROUNDED_ANSWER,
    RETURN_NO_ANSWER,
    filter_by_quality,
    validate_quality_config,
)


def run_chat(
    *,
    query: str,
    llm: LLMProvider,
    embedder: EmbeddingModel,
    store: VectorStore,
    reranker: Reranker | None = None,
    chat_config: ChatConfig | None = None,
    retrieval_config: RetrieverConfig | None = None,
    rewrite_context: str = "",
    session_context: str = "",
    history: History | None = None,
) -> dict:
    """Run one RAG chat turn and return structured output."""
    cfg = chat_config or ChatConfig()
    error = _validate_query(query)
    if error:
        return _response(answer="", history=history, errors=[error])
    quality_error = validate_quality_config(cfg.retrieval_quality)
    if quality_error:
        return _response(answer="", history=history, errors=[quality_error])

    intent = detect_intent(query) if cfg.use_intent_routing else RAG_INTENT
    if should_bypass_retrieval(intent):
        return _run_direct_llm(
            query=query,
            llm=llm,
            cfg=cfg,
            history=history,
            intent=intent,
        )

    retrieval = run_retrieval(
        query=query,
        model=embedder,
        store=store,
        rewrite_llm=llm,
        reranker=reranker,
        config=retrieval_config or RetrieverConfig(),
        rewrite_context=rewrite_context or cfg.persona,
        session_context=session_context,
    )
    if retrieval["errors"]:
        return _response(answer="", history=history, retrieval=retrieval, errors=retrieval["errors"], intent=intent)

    selected, quality = filter_by_quality(retrieval["outputs"], cfg.retrieval_quality)
    if quality["status"] == "low_confidence":
        return _handle_low_confidence(
            query=query,
            llm=llm,
            cfg=cfg,
            history=history,
            retrieval=retrieval,
            quality=quality,
            intent=intent,
        )

    context = build_context(selected)
    sources = extract_sources(selected)
    system = build_system_prompt(cfg)
    user = build_user_prompt(query, context)

    try:
        llm_response = llm.complete(system=system, user=user, history=list(history or []))
    except Exception as e:
        return _response(
            answer="",
            history=history,
            retrieval=retrieval,
            sources=sources,
            errors=[_failure(stage="generate", error=str(e), is_retryable=True)],
            intent=intent,
        )

    answer = validate_citations(llm_response.text, sources) if sources else llm_response.text
    updated_history = _append_history(history, query=query, answer=answer)
    return _response(
        answer=answer,
        history=updated_history,
        retrieval=retrieval,
        sources=sources,
        llm={
            "provider": llm_response.provider,
            "model": llm_response.model,
            "input_tokens": llm_response.input_tokens,
            "output_tokens": llm_response.output_tokens,
        },
        intent=intent,
        retrieval_quality=quality,
    )


def _run_direct_llm(
    *,
    query: str,
    llm: LLMProvider,
    cfg: ChatConfig,
    history: History | None,
    intent: str,
) -> dict:
    system = build_system_prompt(cfg)
    try:
        llm_response = llm.complete(system=system, user=query, history=list(history or []))
    except Exception as e:
        return _response(
            answer="",
            history=history,
            errors=[_failure(stage="generate", error=str(e), is_retryable=True)],
            intent=intent,
        )

    updated_history = _append_history(history, query=query, answer=llm_response.text)
    return _response(
        answer=llm_response.text,
        history=updated_history,
        llm={
            "provider": llm_response.provider,
            "model": llm_response.model,
            "input_tokens": llm_response.input_tokens,
            "output_tokens": llm_response.output_tokens,
        },
        intent=intent,
        retrieval_quality={"status": "skipped", "reason": "intent_bypass"},
    )


def _handle_low_confidence(
    *,
    query: str,
    llm: LLMProvider,
    cfg: ChatConfig,
    history: History | None,
    retrieval: dict,
    quality: dict,
    intent: str,
) -> dict:
    if quality["mode"] == RETURN_NO_ANSWER:
        return _response(
            answer="",
            history=history,
            retrieval=retrieval,
            errors=[_failure(stage="quality", error="retrieval quality below configured threshold")],
            intent=intent,
            retrieval_quality=quality,
        )

    if quality["mode"] == ASK_CLARIFYING_QUESTION:
        user = (
            "The retrieved context was not confident enough to answer. "
            f"Ask one concise clarifying question for this user query: {query}"
        )
    elif quality["mode"] == REFUSE_GROUNDED_ANSWER:
        user = (
            "The retrieved context was not confident enough to answer reliably. "
            "Respond naturally that there is not enough relevant context to give a grounded answer, "
            "and ask the user to rephrase or provide more detail."
        )
    else:
        user = (
            "The retrieved context was not confident enough to ground the answer. "
            "Answer cautiously without claiming the answer came from retrieved context, "
            f"or ask for clarification if needed.\n\nQuestion: {query}"
        )

    try:
        llm_response = llm.complete(system=build_system_prompt(cfg), user=user, history=list(history or []))
    except Exception as e:
        return _response(
            answer="",
            history=history,
            retrieval=retrieval,
            errors=[_failure(stage="generate", error=str(e), is_retryable=True)],
            intent=intent,
            retrieval_quality=quality,
        )

    updated_history = _append_history(history, query=query, answer=llm_response.text)
    return _response(
        answer=llm_response.text,
        history=updated_history,
        retrieval=retrieval,
        llm={
            "provider": llm_response.provider,
            "model": llm_response.model,
            "input_tokens": llm_response.input_tokens,
            "output_tokens": llm_response.output_tokens,
        },
        intent=intent,
        retrieval_quality=quality,
    )


def _append_history(history: History | None, *, query: str, answer: str) -> History:
    updated = list(history or [])
    updated.append({"role": "user", "content": query})
    updated.append({"role": "assistant", "content": answer})
    return updated


def _validate_query(query: str) -> dict | None:
    if not isinstance(query, str) or not query.strip():
        return _failure(stage="validate", error="query must be a non-empty string")
    return None


def _response(
    *,
    answer: str,
    history: History | None,
    retrieval: dict | None = None,
    sources: list[dict] | None = None,
    llm: dict | None = None,
    errors: list[dict] | None = None,
    intent: str = RAG_INTENT,
    retrieval_quality: dict | None = None,
) -> dict:
    return {
        "answer": answer,
        "sources": sources or [],
        "history": list(history or []),
        "retrieval": retrieval or {"retrieved": 0, "failed": 0, "outputs": [], "errors": []},
        "llm": llm or {},
        "errors": errors or [],
        "intent": intent,
        "retrieval_quality": retrieval_quality or {"status": "not_evaluated"},
    }


def _failure(*, stage: str, error: str, is_retryable: bool = False) -> dict:
    return {
        "source": "",
        "source_kind": "chat",
        "stage": stage,
        "error": error,
        "isRetryable": is_retryable,
        "attempts": 1,
    }
