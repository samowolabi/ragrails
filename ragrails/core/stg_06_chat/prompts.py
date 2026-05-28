from __future__ import annotations

from .config import ChatConfig


SYSTEM_PROMPT = """{persona}
When context is provided, answer using only that context.
Be concise and precise.
When referencing endpoints, parameters, code, or facts from context, cite with inline chunk citations like [C1] or [C2].
Use only citation IDs that appear in the context.
If no context is provided, answer naturally or ask a clarifying question."""


def build_system_prompt(config: ChatConfig) -> str:
    persona = config.persona or "You are a helpful assistant."
    return SYSTEM_PROMPT.format(persona=persona)


def build_user_prompt(query: str, context: str) -> str:
    if not context:
        return query
    return f"Context:\n\n{context}\n\nQuestion: {query}"
