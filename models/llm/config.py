from dataclasses import dataclass

from .base import LLMProvider
from .providers import PROVIDERS
from .registry import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, DEFAULT_PROVIDER, require


@dataclass
class LLMConfig:
    provider:   str = DEFAULT_PROVIDER
    model:      str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS


def create_llm(config: LLMConfig) -> LLMProvider:
    """Instantiate an LLM provider from config.

    Example:
        llm = create_llm(LLMConfig())
        # → provider instance for the configured model
    """
    info = require(config.model)
    provider = config.provider or info.provider
    if provider != info.provider:
        raise ValueError(
            f"Model {config.model!r} belongs to provider {info.provider!r}, not {provider!r}."
        )
    if provider not in PROVIDERS:
        raise ValueError(f"Unknown LLM provider: {provider!r}")
    return PROVIDERS[provider].create(model=config.model, max_tokens=config.max_tokens)
