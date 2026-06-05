import os
from dataclasses import dataclass, field
from typing import Iterator

from dotenv import load_dotenv

from ..base import History, LLMProvider, LLMResponse, LLMToolResponse, ToolLoopMessage
from .catalog import GOOGLE_MODELS

load_dotenv()

PROVIDER = "google"
MODELS = GOOGLE_MODELS


@dataclass
class GoogleProvider(LLMProvider):
    model: str = "gemini-3-pro"
    max_tokens: int = 0
    _client: object = field(init=False, repr=False, default=None)

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be provided by the LLM factory.")

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:
                raise RuntimeError('Google Gemini support requires: pip install "ragrails[google]"') from exc
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set.")
            self._client = genai.Client(api_key=api_key)
        return self._client

    def complete(
        self,
        system: str,
        user: str,
        history: History | None = None,
        temperature: float | None = None,
    ) -> LLMResponse:
        response = self._get_client().models.generate_content(
            model=self.model,
            contents=_to_google_contents(user=user, history=history),
            config=_generation_config(
                system=system,
                max_tokens=self.max_tokens,
                temperature=temperature,
            ),
        )
        input_tokens, output_tokens = _usage_tokens(response)
        return LLMResponse(
            text=getattr(response, "text", "") or "",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=self.model,
            provider=PROVIDER,
        )

    def complete_with_tools(
        self,
        messages: list[ToolLoopMessage],
        system: str,
        tools: list[dict],
    ) -> LLMToolResponse:
        if tools:
            raise NotImplementedError("Google Gemini tool calling is not implemented yet.")

        text = "\n\n".join(
            f"{getattr(message, 'role', 'user')}: {getattr(message, 'content', '')}"
            for message in messages
            if hasattr(message, "content")
        )
        response = self.complete(system=system, user=text)
        return LLMToolResponse(
            text=response.text,
            tool_calls=[],
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            model=response.model,
            provider=response.provider,
        )

    def stream(
        self,
        system: str,
        user: str,
        history: History | None = None,
        temperature: float | None = None,
    ) -> Iterator[str]:
        stream = self._get_client().models.generate_content_stream(
            model=self.model,
            contents=_to_google_contents(user=user, history=history),
            config=_generation_config(
                system=system,
                max_tokens=self.max_tokens,
                temperature=temperature,
            ),
        )
        for chunk in stream:
            text = getattr(chunk, "text", "") or ""
            if text:
                yield text


def create(model: str, max_tokens: int) -> GoogleProvider:
    return GoogleProvider(model=model, max_tokens=max_tokens)


def _generation_config(system: str, max_tokens: int, temperature: float | None) -> dict:
    config = {
        "system_instruction": system,
        "max_output_tokens": max_tokens,
    }
    if temperature is not None:
        config["temperature"] = temperature
    return config


def _to_google_contents(user: str, history: History | None) -> list[dict]:
    contents = []
    for turn in history or []:
        role = "model" if turn.get("role") == "assistant" else "user"
        contents.append({
            "role": role,
            "parts": [{"text": turn.get("content", "")}],
        })
    contents.append({
        "role": "user",
        "parts": [{"text": user}],
    })
    return contents


def _usage_tokens(response) -> tuple[int, int]:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return 0, 0
    input_tokens = getattr(usage, "prompt_token_count", 0) or 0
    output_tokens = getattr(usage, "candidates_token_count", 0) or 0
    return input_tokens, output_tokens
