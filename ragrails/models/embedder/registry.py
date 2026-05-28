from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from .base import EmbeddingModel


EmbedderFactory = Callable[..., EmbeddingModel]


@dataclass(frozen=True)
class EmbedderInfo:
    provider: str
    default_model: str
    models: tuple[str, ...] = ()


@dataclass(frozen=True)
class _EmbedderSpec:
    info: EmbedderInfo
    factory: EmbedderFactory | str


EMBEDDER_SPECS: dict[str, _EmbedderSpec] = {
    "voyage": _EmbedderSpec(
        info=EmbedderInfo(
            provider="voyage",
            default_model="voyage-3",
            models=("voyage-3-lite", "voyage-3", "voyage-3-large"),
        ),
        factory="ragrails.models.embedder.voyage:VoyageModel",
    )
}


def list_embedders() -> list[EmbedderInfo]:
    return [spec.info for spec in EMBEDDER_SPECS.values()]


def register_embedder(
    provider: str,
    factory: EmbedderFactory,
    *,
    default_model: str,
    models: tuple[str, ...] = (),
    replace: bool = False,
) -> None:
    if not provider:
        raise ValueError("provider is required")
    if provider in EMBEDDER_SPECS and not replace:
        raise ValueError(f"Embedder provider already registered: {provider!r}")

    EMBEDDER_SPECS[provider] = _EmbedderSpec(
        info=EmbedderInfo(provider=provider, default_model=default_model, models=models),
        factory=factory,
    )


def create_embedder(
    provider: str = "voyage",
    *,
    model: str | None = None,
    input_type: str = "document",
    **options: Any,
) -> EmbeddingModel:
    if provider not in EMBEDDER_SPECS:
        available = ", ".join(sorted(EMBEDDER_SPECS))
        raise ValueError(f"Unknown embedder provider '{provider}'. Available providers: {available}")

    spec = EMBEDDER_SPECS[provider]
    info = spec.info
    factory = _load_factory(spec.factory)
    return factory(
        model_name=model or info.default_model,
        input_type=input_type,
        **options,
    )


def _load_factory(factory: object) -> EmbedderFactory:
    if callable(factory):
        return factory
    if not isinstance(factory, str):
        raise TypeError("embedder factory must be a callable or import path")

    module_name, class_name = factory.split(":", 1)
    module = import_module(module_name)
    return getattr(module, class_name)
