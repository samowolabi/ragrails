"""
Intent classifier — detects conversational queries that don't need retrieval.

is_conversational() is rule-based (no LLM call) so it adds zero latency and cost.
When it returns True, the caller should skip rewrite / retrieve / rerank entirely
and pass the query straight to the LLM with existing history.
"""

import re


# Common greeting and social phrases — extend as needed
_CONVERSATIONAL_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        # Greetings
        r"^(hi|hey|hello|howdy|hiya|yo)\b",
        r"^good\s+(morning|afternoon|evening|night)\b",
        r"^how\s+are\s+(you|u)\b",
        r"^what'?s?\s+up\b",
        # Acknowledgements
        r"^(thanks|thank\s+you|thx|cheers|appreciate\s+it)\b",
        r"^(ok|okay|got\s+it|understood|noted|sure|alright|cool|great|nice|perfect|sounds\s+good)\b",
        r"^(yes|no|yeah|nope|yep|nah)\b",
        # Farewells
        r"^(bye|goodbye|see\s+you|cya|later|take\s+care)\b",
        # Casual
        r"^(lol|haha|lmao|hehe)\b",
        # Meta questions about the assistant
        r"^who\s+are\s+you\b",
        r"^what\s+is\s+your\s+name\b",
        r"^what\s+(can|do)\s+you\s+do\b",
        r"^(help|help\s+me)\s*$",
        # Time / date — no knowledge base can answer these
        r"^what\s+(is\s+)?(the\s+)?(time|date|day|today)\b",
        r"^what\s+time\s+is\s+it\b",
    ]
]

# Queries below this word count are also checked against patterns
_SHORT_QUERY_THRESHOLD = 4


def is_conversational(query: str) -> bool:
    """Return True if the query is a greeting or social message that needs no retrieval.

    Example:
        is_conversational("hello")          # → True
        is_conversational("thanks!")        # → True
        is_conversational("how do I send money")  # → False
    """
    text = query.strip()
    if not text:
        return False

    word_count = len(text.split())

    # Only apply patterns to short queries — avoids false positives on longer questions
    # that happen to start with a social word (e.g. "Hey, how do I verify my account?")
    if word_count <= _SHORT_QUERY_THRESHOLD:
        for pattern in _CONVERSATIONAL_PATTERNS:
            if pattern.search(text):
                return True

    return False
