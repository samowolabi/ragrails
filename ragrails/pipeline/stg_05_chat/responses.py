"""Response types for chat generation.

This module intentionally stays small: it defines the object that moves through
the chat pipeline after any generation path finishes.

Example:
    response = GeneratorResponse(
        answer="Use the Authorization header with a Bearer token.",
        sources=[{"id": "C1", "title": "API Basics", "heading": "Authentication", "path": "https://example.com/api"}],
        history=[
            {"role": "user", "content": "How do I authenticate?"},
            {"role": "assistant", "content": "Use the Authorization header..."},
        ],
    )

    if not response.rendered:
        ui.print_answer(response.answer, response.sources)
"""

from dataclasses import dataclass, field

from ragrails.models.llm.base import History


@dataclass
class GeneratorResponse:
    """A completed chat generation result.

    Attributes:
        answer: The final assistant text. Empty string means generation failed
            or no answer was produced.
        sources: Chunk-level source references extracted from retrieved chunks.
            The terminal UI renders these below the answer so inline citations
            like `[C1]` map to exact chunks.
        history: Updated chat history including the user query and assistant
            answer. The pipeline stores this back on the session.
        rendered: True when the response has already been printed to the UI.
            Streaming generation prints tokens while they arrive, so the REPL
            uses this flag to avoid printing the same answer twice.

    Example:
        response = GeneratorResponse(answer="Hello!", rendered=False)
        assert response.answer == "Hello!"
    """

    answer: str
    sources: list[dict] = field(default_factory=list)
    history: History = field(default_factory=list)
    rendered: bool = False
