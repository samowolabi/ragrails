"""Plain chat generation for the legacy session/REPL path.

This module owns the non-tool generation path:
1. Format retrieved chunks into prompt context.
2. Build a system prompt and user prompt.
3. Call `llm.complete()` or `llm.stream()`.
4. Package the answer, sources, and updated history.

The reusable core chat path lives in `chat.py`. This module remains for the
existing REPL/session flow and reuses the core context helpers.

Example:
    response = generate(
        query="How do I authenticate?",
        results=retrieved_chunks,
        llm=session.llm,
        config=session.chat_config,
        history=session.history,
    )
    session.history = response.history
"""

from ragrails.models.llm.base import History, LLMProvider
from ragrails.models.llm import usage_logger
from ragrails.models.vector_db.base import SearchResult

from . import ui
from ragrails.core.stg_06_chat.config import ChatConfig
from ragrails.core.stg_06_chat.context import build_context, extract_sources, select_context, validate_citations
from .responses import GeneratorResponse


SYSTEM_PROMPT = """{persona}
When answering questions about the product's features, refer to the product in the third person — use "they", "it", or the product name, not "we" or "our".
When context is provided, answer using only that context. Be concise and precise.
When referencing endpoints, parameters, or code, use exact names from the context.
When context is provided, cite every factual claim with inline chunk citations like [C1] or [C2]. Use only citation IDs that appear in the context. Do not cite page titles by themselves.
If no context is provided, respond naturally — greetings, clarifying questions, or off-topic messages are fine."""

TOOL_RULES = """

Tool calling rules:
- Never call a tool with missing or placeholder values. Ask for each missing field first.
- For api_call: always include method, url, headers, params, and body. Use {} only for genuinely empty headers, params, or body.
- For api_call: put the Bearer token in headers as {"Authorization": "Bearer <token>"}, put all request body fields in the body object (not as separate arguments).
- Extract exact values from the conversation — do not substitute placeholders like YOUR_SECRET_KEY.
- Only call the tool once you have every required field confirmed.
- If the user asks what request, cURL, or API call you used previously, do not call a tool again — answer from the conversation/tool history."""


def prepare_prompt(query: str, results: list[SearchResult], cfg: ChatConfig) -> tuple[list[SearchResult], str, str]:
    """Filter retrieval results and build `(filtered, system, user)` prompts.

    Results below `cfg.min_rerank_score` are excluded from the context. If no
    chunks survive filtering, the user prompt is just the raw query, allowing the
    model to answer naturally for greetings or off-topic messages.

    Args:
        query: The user-facing query, not the rewritten retrieval query.
        results: Reranked retrieval candidates.
        cfg: Chat configuration controlling persona and rerank threshold.

    Example:
        filtered, system, user = prepare_prompt("How do I pay?", results, cfg)
        assert "Question:" in user or user == "How do I pay?"
    """
    filtered = select_context(results, min_score=cfg.min_rerank_score)
    system = SYSTEM_PROMPT.format(persona=cfg.persona or "You are a helpful assistant.")

    if filtered:
        user = f"Context:\n\n{build_context(filtered)}\n\nQuestion: {query}"
    else:
        user = query

    return filtered, system, user


def finish_response(
    query: str,
    answer: str,
    history: History | None,
    filtered: list[SearchResult],
    rendered: bool = False,
) -> GeneratorResponse:
    """Append the turn to history and return a `GeneratorResponse`.

    The original user query is stored in history, not the rewritten retrieval
    query. This keeps future conversational context human-readable.

    Args:
        query: Original user query.
        answer: Final assistant answer text.
        history: Previous conversation messages.
        filtered: Chunks actually used in the prompt context.
        rendered: True when the UI has already printed the response.

    Example:
        response = finish_response("Hi", "Hello!", [], [], rendered=False)
        assert response.history[-2]["role"] == "user"
        assert response.history[-1]["role"] == "assistant"
    """
    updated = list(history or [])
    updated.append({"role": "user", "content": query})
    updated.append({"role": "assistant", "content": answer})
    sources = extract_sources(filtered) if filtered else []
    return GeneratorResponse(
        answer=validate_citations(answer, sources) if sources else answer,
        sources=sources,
        history=updated,
        rendered=rendered,
    )


def generate(
    query: str,
    results: list[SearchResult],
    llm: LLMProvider,
    config: ChatConfig | None = None,
    history: History | None = None,
    stream: bool = False,
) -> GeneratorResponse:
    """Generate a plain, non-tool answer.

    This path is used when chat tools are disabled, when the active model cannot
    use tools and no fallback is available, or when the query is conversational.
    It still uses retrieved context when `results` is non-empty.

    Set `stream=True` to print chunks as the provider returns them. In that
    case the returned response has `rendered=True`, so the REPL does not print
    it again.

    Example:
        response = generate("How do I authenticate?", results, llm=llm)
        response = generate("How do I authenticate?", results, llm=llm, stream=True)
        # → GeneratorResponse(answer="Use Bearer token...", sources=[...], history=[...])
    """
    cfg = config or ChatConfig()
    filtered, system, user = prepare_prompt(query, results, cfg)

    if stream:
        # Streaming is the one generation path that intentionally renders inside
        # the generator, because tokens need to appear as they arrive.
        ui.stream_open()
        full = ""
        for chunk in llm.stream(system=system, user=user, history=list(history or [])):
            full += chunk
            ui.stream_chunk(chunk)
        ui.stream_close(extract_sources(filtered) if filtered else [])
        return finish_response(query, full, history, filtered, rendered=True)

    response = llm.complete(system=system, user=user, history=list(history or []))
    usage_logger.log(response, action="answer_generation")
    return finish_response(query, response.text, history, filtered)
