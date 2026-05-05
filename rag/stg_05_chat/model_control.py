"""Model selection helpers for chat sessions."""

from dataclasses import dataclass

from models.llm.config import create_llm
from models.llm.registry import MODELS, first_tool_model, get as get_model
from models.llm.types import ModelInfo

from .session import ChatSession


@dataclass(frozen=True)
class ModelSwitch:
    """Result of attempting to switch the active session model."""

    ok: bool
    message: str
    model: ModelInfo | None = None
    switched: bool = False


def all_models() -> list[ModelInfo]:
    """Return all registered models in display order."""
    return MODELS


def switch_model(session: ChatSession, model_name: str) -> ModelSwitch:
    """Switch the active LLM by model name and update provider + provider instance."""
    info = get_model(model_name)
    if info is None:
        return ModelSwitch(
            ok=False,
            message=f"Unknown model '{model_name}'. Run /model to see available options.",
        )

    session.llm_config.provider = info.provider
    session.llm_config.model = info.name
    session.llm = create_llm(session.llm_config)
    return ModelSwitch(ok=True, message=f"{info.provider}/{info.name}", model=info, switched=True)


def ensure_tool_model(session: ChatSession) -> ModelSwitch:
    """Ensure the active session model supports tool calling, switching if needed."""
    current = get_model(session.llm_config.model)
    if current is None:
        return ModelSwitch(
            ok=False,
            message=f"Unknown model {session.llm_config.model!r} — using plain generation",
        )

    if current.supports_tools:
        return ModelSwitch(ok=True, message=f"{current.provider}/{current.name}", model=current)

    fallback = first_tool_model(preferred_provider=current.provider)
    if fallback is None:
        return ModelSwitch(
            ok=False,
            message=f"{current.name} does not support tools and no tool-capable model is configured",
            model=current,
        )

    switched = switch_model(session, fallback.name)
    if not switched.ok:
        return switched

    return ModelSwitch(
        ok=True,
        message=f"{current.name} does not support tools — switched to {fallback.provider}/{fallback.name}",
        model=fallback,
        switched=True,
    )
