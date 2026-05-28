"""SDK chat history helpers."""

from __future__ import annotations


def compact_history(
    history: list[dict],
    *,
    llm,
    history_limit: int | None = 15,
    keep_recent: int = 5,
    enabled: bool = True,
) -> tuple[list[dict], bool]:
    """Compact old messages and keep the most recent messages."""
    if not enabled or history_limit is None or len(history) < history_limit:
        return list(history), False

    recent = list(history[-keep_recent:])
    older = history[:-keep_recent]
    summary = summarize_messages(older, llm=llm)
    return [{"role": "system", "content": f"Conversation summary: {summary}"}] + recent, True


def summarize_messages(messages: list[dict], *, llm) -> str:
    text = "\n".join(
        f"{item.get('role', 'unknown')}: {item.get('content', '')}"
        for item in messages
    )
    response = llm.complete(
        system="Summarize this conversation history for future RAG chat turns. Keep durable user goals, constraints, decisions, and unresolved questions.",
        user=text,
        history=[],
        temperature=0.0,
    )
    return response.text.strip()
