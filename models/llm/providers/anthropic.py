import os
from dataclasses import dataclass, field
from typing import Iterator

import anthropic
from dotenv import load_dotenv

from ..base import (
    AssistantToolCallMessage,
    ChatMessage,
    History,
    LLMProvider,
    LLMResponse,
    LLMToolResponse,
    ToolCall,
    ToolLoopMessage,
    ToolResultMessage,
)
from ..types import ModelInfo

load_dotenv()

PROVIDER = "anthropic"

MODELS: list[ModelInfo] = [
    ModelInfo("claude-haiku-4-5-20251001", PROVIDER, "fast & cheap    — lightweight tasks",    0.80, 4.00, supports_tools=True),
    ModelInfo("claude-sonnet-4-6",         PROVIDER, "capable         — balanced performance", 3.00, 15.00, supports_tools=True),
    ModelInfo("claude-opus-4-7",           PROVIDER, "most capable    — complex reasoning",   15.00, 75.00, supports_tools=True),
]


@dataclass
class AnthropicProvider(LLMProvider):
    model: str = "claude-haiku-4-5-20251001"
    max_tokens: int = 0
    _client: anthropic.Anthropic = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be provided by the LLM factory.")

    def _get_client(self) -> anthropic.Anthropic:
        if self._client is None:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable not set.")
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def complete(
        self,
        system: str,
        user: str,
        history: History | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        messages = [{"role": t["role"], "content": t["content"]} for t in (history or [])]
        messages.append({"role": "user", "content": user})

        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": messages,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        message = self._get_client().messages.create(**kwargs)
        return LLMResponse(
            text=_text_from_content(message.content),
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            model=self.model,
            provider=PROVIDER,
        )

    def complete_with_tools(
        self,
        messages: list[ToolLoopMessage],
        system: str,
        tools: list[dict],
    ) -> LLMToolResponse:
        message = self._get_client().messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=_to_anthropic_messages(messages),
            tools=_to_anthropic_tools(tools),
        )

        tool_calls = [
            ToolCall(id=block.id, name=block.name, arguments=block.input)
            for block in message.content
            if getattr(block, "type", "") == "tool_use"
        ]

        return LLMToolResponse(
            text=_text_from_content(message.content) or None,
            tool_calls=tool_calls,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            model=self.model,
            provider=PROVIDER,
        )

    def stream(
        self,
        system: str,
        user: str,
        history: History | None = None,
        temperature: float | None = None,
    ) -> Iterator[str]:
        """Stream text deltas using Anthropic's messages stream manager.

        Anthropic does not stream in the same shape as OpenAI chat completions.
        The SDK returns a context manager whose `text_stream` iterator yields
        only text deltas, so the provider adapts that into our shared
        `Iterator[str]` contract.

        Example:
            for chunk in AnthropicProvider(max_tokens=2048).stream("You are helpful.", "Hi"):
                print(chunk, end="", flush=True)
        """
        messages = [{"role": t["role"], "content": t["content"]} for t in (history or [])]
        messages.append({"role": "user", "content": user})

        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": messages,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        with self._get_client().messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                if text:
                    yield text


def create(model: str, max_tokens: int) -> AnthropicProvider:
    return AnthropicProvider(model=model, max_tokens=max_tokens)


def _text_from_content(content: list) -> str:
    return "".join(block.text for block in content if getattr(block, "type", "") == "text")


def _to_anthropic_tools(tools: list[dict]) -> list[dict]:
    out = []
    for tool in tools:
        out.append({
            "name": tool["name"],
            "description": tool.get("description", ""),
            "input_schema": tool.get("input_schema", {"type": "object", "properties": {}}),
        })
    return out


def _to_anthropic_messages(messages: list[ToolLoopMessage]) -> list[dict]:
    out = []

    def flush_tool_results(results: list[ToolResultMessage]) -> None:
        if not results:
            return
        out.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": result.tool_call_id,
                    "content": result.content,
                }
                for result in results
            ],
        })
        results.clear()

    pending_tool_results: list[ToolResultMessage] = []
    for msg in messages:
        if isinstance(msg, ChatMessage):
            flush_tool_results(pending_tool_results)
            out.append({"role": msg.role, "content": msg.content})
            continue

        if isinstance(msg, AssistantToolCallMessage):
            flush_tool_results(pending_tool_results)
            content = []
            if msg.content:
                content.append({"type": "text", "text": msg.content})
            for tc in msg.tool_calls:
                content.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                })
            out.append({"role": "assistant", "content": content})
            continue

        if isinstance(msg, ToolResultMessage):
            pending_tool_results.append(msg)
            continue

        raise TypeError(f"Unsupported tool-loop message: {type(msg).__name__}")

    flush_tool_results(pending_tool_results)
    return out
