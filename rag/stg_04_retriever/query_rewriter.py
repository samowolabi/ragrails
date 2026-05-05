"""
Query rewriter — translates a natural language question into expanded
technical language before vector retrieval.
"""

from models.llm.base import LLMProvider
from models.llm import usage_logger


_SYSTEM = """You are a query rewriter for a documentation search system.
Your job is to produce a standalone search query that captures the user's full intent.

Rules:
- Use the conversation context to resolve pronouns and references ("they", "it", "that feature")
- If the question is about a specific operation or integration, add relevant technical terms
- If the question is conceptual (what is X, how does X work), keep it conceptual but more specific
- If the question is conversational (greetings, corrections, thanks), return it unchanged
- Do not force every question into API/endpoint format
- Do not expand or guess the meaning of acronyms or abbreviations — keep them exactly as written
- Return only the rewritten query — no explanation, no punctuation at the end"""

_PROMPT = """{context_section}Current query: {query}"""


def rewrite(query: str, llm: LLMProvider, context: str = "", session_context: str = "") -> str:
    """Rewrite a natural language query into a standalone search query.

    Example:
        rewrite("Do they support Nigeria?", llm=llm, context="Acme API", session_context="User is asking about supported countries.")
        # → "does Acme API support Nigeria"
    """
    # XML tags are used to clearly delimit the session context from the query,
    # preventing the LLM from confusing prior conversation content with the current request.
    parts = []
    if context:
        parts.append(f"Documentation: {context}")
    if session_context:
        parts.append(f"<conversation_context>\n{session_context}\n</conversation_context>")

    context_section = "\n\n".join(parts) + "\n\n" if parts else ""
    user = _PROMPT.format(context_section=context_section, query=query)

    response = llm.complete(system=_SYSTEM, user=user)
    print(f"\n  \033[36mQuery rewrite:\033[0m {query}\n  \033[36m→\033[0m {response.text}")
    usage_logger.log(response, action="query_rewrite")
    return response.text
