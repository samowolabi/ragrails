"""Provider-aggregated model registry."""

from .providers import PROVIDERS
from .types import ModelInfo

DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL    = "gpt-4o"
DEFAULT_MAX_TOKENS = 2048

MODELS: list[ModelInfo] = [
    model
    for provider in PROVIDERS.values()
    for model in provider.MODELS
]

_BY_NAME: dict[str, ModelInfo] = {m.name: m for m in MODELS}


def get(name: str) -> ModelInfo | None:
    """Return ModelInfo for a model name, or None if not registered.

    Example:
        get("gpt-4o").input_price  # → 2.50
    """
    return _BY_NAME.get(name)


def require(name: str) -> ModelInfo:
    """Return ModelInfo or raise a clear error."""
    info = get(name)
    if info is None:
        raise ValueError(f"Unknown LLM model: {name!r}")
    return info


def by_provider(provider: str) -> list[ModelInfo]:
    """Return all models for a given provider.

    Example:
        by_provider("openai")  # → [ModelInfo("gpt-4o-mini", ...), ...]
    """
    return [m for m in MODELS if m.provider == provider]


def first_tool_model(preferred_provider: str = "") -> ModelInfo | None:
    """Return the first tool-capable model, preferring a provider when supplied."""
    if preferred_provider:
        for model in by_provider(preferred_provider):
            if model.supports_tools:
                return model

    for model in MODELS:
        if model.supports_tools:
            return model
    return None


def provider_names() -> list[str]:
    """Return registered provider names."""
    return list(PROVIDERS)


def all_names() -> list[str]:
    """Return all registered model names.

    Example:
        all_names()  # → ["gpt-4o-mini", "gpt-4o", ..., "claude-sonnet-4-6", ...]
    """
    return list(_BY_NAME)
