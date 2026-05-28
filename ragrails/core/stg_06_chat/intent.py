"""Chat intent detection."""

from __future__ import annotations

import re


GREETING_INTENT = "greeting"
THANKS_INTENT = "thanks"
FAREWELL_INTENT = "farewell"
ACKNOWLEDGEMENT_INTENT = "acknowledgement"
RAG_INTENT = "rag"

_INTENT_PATTERNS = {
    GREETING_INTENT: [
        r"^hi[!. ]*$",
        r"^hello[!. ]*$",
        r"^hey[!. ]*$",
        r"^good\s+(morning|afternoon|evening)[!. ]*$",
        r"^how\s+are\s+you\??[!. ]*$",
        r"^what'?s\s+up\??[!. ]*$",
    ],
    THANKS_INTENT: [
        r"^thanks[!. ]*$",
        r"^thank\s+you[!. ]*$",
        r"^thank\s+you\s+very\s+much[!. ]*$",
        r"^thanks\s+(a\s+lot|so\s+much)[!. ]*$",
        r"^appreciate\s+it[!. ]*$",
        r"^much\s+appreciated[!. ]*$",
    ],
    FAREWELL_INTENT: [
        r"^bye[!. ]*$",
        r"^goodbye[!. ]*$",
        r"^see\s+you[!. ]*$",
        r"^talk\s+to\s+you\s+later[!. ]*$",
    ],
    ACKNOWLEDGEMENT_INTENT: [
        r"^ok[!. ]*$",
        r"^okay[!. ]*$",
        r"^alright[!. ]*$",
        r"^got\s+it[!. ]*$",
        r"^sounds\s+good[!. ]*$",
        r"^cool[!. ]*$",
    ],
}

_BYPASS_INTENTS = {
    GREETING_INTENT,
    THANKS_INTENT,
    FAREWELL_INTENT,
    ACKNOWLEDGEMENT_INTENT,
}


def detect_intent(message: str) -> str:
    """Detect whether a message should bypass retrieval."""
    normalized = " ".join(str(message or "").strip().lower().split())
    if not normalized:
        return RAG_INTENT
    for intent, patterns in _INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, normalized):
                return intent
    return RAG_INTENT


def should_bypass_retrieval(intent: str) -> bool:
    return intent in _BYPASS_INTENTS
