"""
Pipeline — orchestrates a single chat turn end-to-end.

run_turn() handles:
1. resolve background tasks from the previous turn (history summary, session context)
2. detect conversational intent
3. rewrite the query, retrieve + rerank docs
4. generate the answer (plain / streaming / agentic)
5. update session state and fire the next round of background tasks
"""

from ragrails.pipeline.stg_04_retriever.query_rewriter import rewrite
from ragrails.pipeline.stg_04_retriever.retriever import rerank, retrieve

from . import ui
from .agentic import generate_agentic
from .debug_trace import RagDebugTrace, snapshot_results
from .generator import generate
from .history import prepend_summary, summarize_dropped_turns, trim_history, update_session_context
from .intent import is_conversational
from .model_control import ensure_tool_model
from .responses import GeneratorResponse
from .session import ChatSession


def run_turn(query: str, session: ChatSession) -> GeneratorResponse:
    """Process one user query end-to-end. Mutates session state.

    Example:
        run_turn("How do I authenticate?", session)
        # → returns response, updates session.history, fires background tasks
    """
    try:
        session.debug_trace = RagDebugTrace(
            original_query=query,
            model=session.llm_config.model,
            provider=session.llm_config.provider,
        )
        _resolve_pending(session)

        if is_conversational(query):
            if session.debug_trace:
                session.debug_trace.conversational = True
                session.debug_trace.generation_mode = "plain"
                session.debug_trace.stream = session.chat_config.stream
                session.debug_trace.tools_enabled = session.chat_config.use_tools
            response = _generate_conversational(query, session)
        else:
            rewritten = _rewrite(query, session)
            ranked    = _retrieve(rewritten, session)
            response  = _generate(query, ranked, session)

        _update_session(query, response, session)
        return response
    except Exception as e:
        ui.error(str(e))
        return GeneratorResponse(answer="", sources=[], history=session.history, rendered=True)


# ── Steps ─────────────────────────────────────────────────────────────────────

def _resolve_pending(session: ChatSession) -> None:
    """Wait on background tasks fired during the previous turn and apply their results.

    Example:
        _resolve_pending(session)
        # → session.session_context updated, summary prepended to history
    """
    if session.pending_context is not None:
        try:
            session.session_context = session.pending_context.result()
        except Exception as e:
            ui.error(f"context: {e}")
        session.pending_context = None

    if session.pending_summary is not None:
        try:
            summary = session.pending_summary.result()
            session.history = prepend_summary(session.history, summary)
        except Exception as e:
            ui.error(f"summary: {e}")
        session.pending_summary = None


def _rewrite(query: str, session: ChatSession) -> str:
    """Expand the query using session context so pronouns resolve correctly. Falls back on error.

    Example:
        _rewrite("do they support NGN?", session)  # → "does BudPay support NGN"
    """
    if not session.chat_config.rewrite_query:
        if session.debug_trace:
            session.debug_trace.rewritten_query = query
        return query
    try:
        rewritten = rewrite(
            query,
            llm             = session.llm,
            context         = session.chat_config.persona,
            session_context = session.session_context,
        )
        if session.debug_trace:
            session.debug_trace.rewritten_query = rewritten
        return rewritten
    except Exception as e:
        ui.warn(f"rewrite failed ({e}) — using original query")
        if session.debug_trace:
            session.debug_trace.rewritten_query = query
        return query


def _retrieve(query: str, session: ChatSession) -> list:
    """Run vector search + rerank. Returns [] on retrieval errors or off-topic queries.

    Example:
        ranked = _retrieve("how do I auth", session)  # → [SearchResult(...), ...]
    """
    cfg  = session.chat_config
    rcfg = session.retriever_config
    if session.debug_trace:
        session.debug_trace.retrieval_top_k = rcfg.top_k
        session.debug_trace.retrieval_candidate_k = max(rcfg.top_k * 2, 20)
        session.debug_trace.min_retrieval_score = cfg.min_retrieval_score
        session.debug_trace.min_rerank_score = cfg.min_rerank_score
    try:
        candidates = retrieve(
            query,
            model = session.embedder,
            store = session.vector_store,
            top_k = max(rcfg.top_k * 2, 20),
        )
        if session.debug_trace:
            session.debug_trace.candidates = snapshot_results(candidates)
        if max((c.score for c in candidates), default=0) < cfg.min_retrieval_score:
            if session.debug_trace:
                best = max((c.score for c in candidates), default=0)
                session.debug_trace.retrieval_skipped_reason = (
                    f"best retrieval score {best:.4f} below threshold {cfg.min_retrieval_score:.4f}"
                )
            return []
        ranked = rerank(query, candidates, model=session.reranker, top_k=rcfg.top_k)
        if session.debug_trace:
            session.debug_trace.ranked = snapshot_results(ranked)
        return ranked
    except Exception as e:
        ui.error(f"retrieval: {e}")
        if session.debug_trace:
            session.debug_trace.retrieval_error = str(e)
        return []


def _generate_conversational(query: str, session: ChatSession) -> GeneratorResponse:
    """Plain LLM call with no retrieval — for greetings, thanks, identity questions."""
    response = generate(
        query, [],
        llm     = session.llm,
        config  = session.chat_config,
        history = session.history,
    )
    return response


def _generate(query: str, ranked: list, session: ChatSession) -> GeneratorResponse:
    """Dispatch to the right generator based on config.

    use_tools=True → agentic unless stream=True. Streaming currently uses the
    plain generation path because the tool loop is multi-step and not streamed.
    """
    cfg = session.chat_config
    try:
        use_tools = cfg.use_tools and not cfg.stream
        if session.debug_trace:
            session.debug_trace.stream = cfg.stream
            session.debug_trace.tools_enabled = cfg.use_tools
            session.debug_trace.used = snapshot_results([
                r for r in ranked
                if (r.rerank_score or 0) >= cfg.min_rerank_score
            ])
        if cfg.stream and cfg.use_tools:
            ui.warn("streaming is enabled — using plain generation without tools for this turn")
        if use_tools:
            switch = ensure_tool_model(session)
            if not switch.ok:
                ui.warn(switch.message)
            elif switch.switched:
                ui.warn(switch.message)
            use_tools = switch.ok
            if session.debug_trace:
                session.debug_trace.model = session.llm_config.model
                session.debug_trace.provider = session.llm_config.provider

        if use_tools:
            if session.debug_trace:
                session.debug_trace.generation_mode = "agentic"
            response = generate_agentic(
                query, ranked,
                llm        = session.llm,
                config     = cfg,
                history    = session.history,
                confirm_fn = ui.confirm_tool_call,
            )
        else:
            if session.debug_trace:
                session.debug_trace.generation_mode = "stream" if cfg.stream else "plain"
            response = generate(
                query, ranked,
                llm     = session.llm,
                config  = cfg,
                history = session.history,
                stream  = cfg.stream,
            )
        return response
    except Exception as e:
        ui.error(str(e))
        return GeneratorResponse(answer="", sources=[], history=session.history)


def _update_session(query: str, response: GeneratorResponse, session: ChatSession) -> None:
    """Persist response history, print stale context, and fire next turn's background tasks.

    Example:
        _update_session("hello", response, session)
        # → session.history updated, pending_context + pending_summary may be set
    """
    session.history = response.history

    if not response.answer:
        return

    if session.session_context:
        ui.info("Past session context", session.session_context, color=ui.YELLOW)

    session.pending_context = session.executor.submit(
        update_session_context,
        query, response.answer, session.session_context, session.llm,
    )
    print()

    session.history, dropped = trim_history(session.history, limit=session.chat_config.history_limit)
    if dropped:
        session.pending_summary = session.executor.submit(
            summarize_dropped_turns, dropped, session.llm,
        )
