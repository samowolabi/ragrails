from dataclasses import dataclass

from .base import LLMProvider
from .providers import PROVIDERS
from .registry import DEFAULT_MAX_TOKENS, DEFAULT_MODEL, DEFAULT_PROVIDER, get


@dataclass
class LLMConfig:
    provider:   str = DEFAULT_PROVIDER
    model:      str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS


def create_llm(config: LLMConfig) -> LLMProvider:
    """Instantiate an LLM provider from config.

    Known catalog models can infer their provider and pricing metadata. Unknown
    model names are allowed when a supported provider is provided explicitly.

    Example:
        llm = create_llm(LLMConfig())
    """
    model = config.model.strip()
    provider = (config.provider or "").strip()
    info = get(model)

    if info is None and not provider:
        raise ValueError(f"Unknown LLM model {model!r}; provide provider explicitly to use a custom model.")

    resolved_provider = provider or info.provider
    if info is not None and provider and provider != info.provider:
        raise ValueError(
            f"Model {model!r} belongs to provider {info.provider!r}, not {provider!r}."
        )
    if resolved_provider not in PROVIDERS:
        raise ValueError(f"Unknown LLM provider: {resolved_provider!r}")
    try:
        return PROVIDERS[resolved_provider].create(model=model, max_tokens=config.max_tokens)
    except ImportError as exc:
        raise RuntimeError(
            f'LLM provider {resolved_provider!r} requires: pip install "ragrails[{resolved_provider}]"'
        ) from exc
