import json
import os
from dataclasses import dataclass, field
from typing import Iterator

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
from .meta import OPENAI_MODELS

load_dotenv()

PROVIDER = "openai"
MODELS = OPENAI_MODELS


@dataclass
class OpenAIProvider(LLMProvider):
    model: str = "gpt-4o-mini"
    max_tokens: int = 0
    _client: object = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be provided by the LLM factory.")

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError('OpenAI support requires: pip install "ragrails[openai]"') from exc
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set.")
            self._client = OpenAI(api_key=api_key)
        return self._client

    def complete(
        self,
        system: str,
        user: str,
        history: History | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        messages = [{"role": "system", "content": system}]
        for turn in (history or []):
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user})

        kwargs = {"model": self.model, "max_completion_tokens": self.max_tokens, "messages": messages}
        if temperature is not None:
            kwargs["temperature"] = temperature

        response = self._get_client().chat.completions.create(**kwargs)
        return LLMResponse(
            text=response.choices[0].message.content or "",
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            model=self.model,
            provider=PROVIDER,
        )

    def complete_with_tools(
        self,
        messages: list[ToolLoopMessage],
        system: str,
        tools: list[dict],
    ) -> LLMToolResponse:
        response = self._get_client().chat.completions.create(
            model=self.model,
            max_completion_tokens=self.max_tokens,
            messages=[{"role": "system", "content": system}] + _to_openai_messages(messages),
            tools=_to_openai_tools(tools) or None,
            tool_choice="auto" if tools else None,
        )

        message = response.choices[0].message
        tool_calls = [
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments),
            )
            for tc in (message.tool_calls or [])
        ]

        return LLMToolResponse(
            text=message.content,
            tool_calls=tool_calls,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
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
        messages = [{"role": "system", "content": system}]
        for turn in (history or []):
            messages.append({"role": turn["role"], "content": turn["content"]})
        messages.append({"role": "user", "content": user})

        kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "max_completion_tokens": self.max_tokens,
            "stream": True,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature

        for chunk in self._get_client().chat.completions.create(**kwargs):
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


def create(model: str, max_tokens: int) -> OpenAIProvider:
    return OpenAIProvider(model=model, max_tokens=max_tokens)


def _to_openai_tools(tools: list[dict]) -> list[dict]:
    """Convert neutral tool specs into OpenAI chat-completions tool format."""
    out = []
    for tool in tools:
        fn = {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
        }
        if tool.get("strict"):
            fn["strict"] = True
        out.append({"type": "function", "function": fn})
    return out


def _to_openai_messages(messages: list[ToolLoopMessage]) -> list[dict]:
    """Convert neutral tool-loop messages into OpenAI chat-completions messages."""
    out = []
    for msg in messages:
        if isinstance(msg, ChatMessage):
            out.append({"role": msg.role, "content": msg.content})
            continue

        if isinstance(msg, AssistantToolCallMessage):
            out.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
                    }
                    for tc in msg.tool_calls
                ],
            })
            continue

        if isinstance(msg, ToolResultMessage):
            out.append({"role": "tool", "tool_call_id": msg.tool_call_id, "content": msg.content})
            continue

        raise TypeError(f"Unsupported tool-loop message: {type(msg).__name__}")
    return out
