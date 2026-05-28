"""
History manager — handles trimming and background summarization of conversation history.
When the history limit is reached, dropped turns are summarized in a background thread
so the current chat response is never blocked.
"""

from ragrails.models.llm.base import History, LLMProvider


_SUMMARY_SYSTEM = """You are a conversation summarizer.
Summarize the key points from the provided conversation turns in 2-4 sentences.
Focus on: topics discussed, questions asked, answers given, and specific items referenced."""

_SUMMARY_PROMPT = """Summarize the following conversation turns into key points:

<turns>
{turns_text}
</turns>

Return only the summary — no explanation."""

_CONTEXT_SYSTEM = "You are a conversation context tracker."

_CONTEXT_PROMPT = """Current context:
{current_context}

Latest exchange:
User: {query}
Assistant: {answer}

Update the context in 1-3 sentences. Capture: product discussed, key topics, specific items referenced.
Return only the updated context — no explanation."""


def summarize_dropped_turns(dropped: History, llm: LLMProvider) -> str:
    """Summarize dropped history turns into a compact string.

    Called in a background thread when history is trimmed — never blocks the current chat response.

    Example:
        summary = summarize_dropped_turns(dropped_turns, llm)
        # → "User asked about supported countries and payout options."
    """
    lines = []
    for msg in dropped:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")

    try:
        prompt   = _SUMMARY_PROMPT.format(turns_text="\n".join(lines))
        response = llm.complete(system=_SUMMARY_SYSTEM, user=prompt, temperature=0.0)
        return response.text
    except Exception as e:
        print(f"  [history summary error] {e}")
        return ""


def update_session_context(query: str, answer: str, current_context: str, llm: LLMProvider) -> str:
    """Produce an updated session context summary from the latest exchange.

    Called in a background thread after each turn — never blocks the current chat response.

    Example:
        ctx = update_session_context("What APIs does BudPay offer?", "BudPay offers...", "", llm)
        # → "User asked about BudPay's API offerings. Topics covered: payment acceptance, transfers."
    """
    try:
        prompt   = _CONTEXT_PROMPT.format(
            current_context = current_context or "None yet.",
            query           = query,
            answer          = answer[:600],
        )
        response = llm.complete(system=_CONTEXT_SYSTEM, user=prompt, temperature=0.0)
        return response.text.strip()
    except Exception as e:
        print(f"  [context update error] {e}")
        return current_context


def trim_history(history: History, limit: int) -> tuple[History, History]:
    """Split history into kept and dropped turns based on the limit.

    Example:
        kept, dropped = trim_history(history, limit=20)
        # kept   → last 40 messages (20 turns)
        # dropped → everything before that
    """
    # limit * 2 because each turn is 2 messages (user + assistant)
    max_messages = limit * 2
    if len(history) <= max_messages:
        return history, []
    return history[-max_messages:], history[:-max_messages]


def prepend_summary(history: History, summary: str) -> History:
    """Prepend a summary of dropped turns as a synthetic turn at the start of history.

    The synthetic turn uses a user/assistant pair so the history format stays valid
    for LLM APIs that require alternating roles.

    Example:
        history = prepend_summary(history, "User asked about payouts.")
        # → [{"role": "user", "content": "[Summary]: ..."}, {"role": "assistant", ...}, ...rest]
    """
    return [
        {"role": "user",      "content": f"[Summary of earlier conversation]: {summary}"},
        {"role": "assistant", "content": "Understood, I'll keep that context in mind."},
    ] + history
