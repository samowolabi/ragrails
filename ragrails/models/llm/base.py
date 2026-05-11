from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str


@dataclass
class ToolCall:
    id:        str
    name:      str
    arguments: dict  # parsed from the JSON string the LLM returns


@dataclass
class ChatMessage:
    """Provider-neutral text message used by tool-capable conversations."""
    role: str
    content: str


@dataclass
class AssistantToolCallMessage:
    """Provider-neutral assistant message that records requested tool calls."""
    tool_calls: list[ToolCall]
    content: str | None = None


@dataclass
class ToolResultMessage:
    """Provider-neutral tool result linked to an assistant tool call."""
    tool_call_id: str
    content: str


@dataclass
class LLMToolResponse:
    """Returned by complete_with_tools(). text is None when the LLM issued tool calls instead of answering."""
    text:          str | None
    tool_calls:    list[ToolCall] = field(default_factory=list)
    input_tokens:  int = 0
    output_tokens: int = 0
    model:         str = ""
    provider:      str = ""


# A single conversation turn: {"role": "user" | "assistant", "content": "..."}
History = list[dict]
ToolLoopMessage = ChatMessage | AssistantToolCallMessage | ToolResultMessage


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, history: History | None = None, temperature: float | None = None) -> LLMResponse:
        """Send a prompt and return a response with text and token counts.

        Example:
            llm = create_llm(LLMConfig())
            response = llm.complete(system="You are helpful.", user="What is RAG?", temperature=0.0)
            # → LLMResponse(text="RAG stands for...", input_tokens=12, output_tokens=45, ...)
        """
        ...

    @abstractmethod
    def complete_with_tools(
        self,
        messages: list[ToolLoopMessage],
        system: str,
        tools: list[dict],
    ) -> LLMToolResponse:
        """Send a tool-capable conversation and return text or tool calls.

        Providers adapt neutral tool messages and tool specs into their own API format.
        """
        ...

    def stream(self, system: str, user: str, history: History | None = None, temperature: float | None = None) -> Iterator[str]:
        """Stream response tokens one chunk at a time.

        Providers that support streaming should override this method.
        Default falls back to complete() and yields the full response as a single chunk.

        Example:
            for chunk in llm.stream(system="You are helpful.", user="What is RAG?"):
                print(chunk, end="", flush=True)
        """
        response = self.complete(system=system, user=user, history=history, temperature=temperature)
        yield response.text
