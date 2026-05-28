from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from .base import Reranker


RerankerFactory = Callable[..., Reranker]


@dataclass(frozen=True)
class RerankerInfo:
    provider: str
    default_model: str
    models: tuple[str, ...] = ()


@dataclass(frozen=True)
class _RerankerSpec:
    info: RerankerInfo
    factory: RerankerFactory | str


RERANKER_SPECS: dict[str, _RerankerSpec] = {
    "bm25": _RerankerSpec(
        info=RerankerInfo(
            provider="bm25",
            default_model="bm25",
            models=("bm25",),
        ),
        factory="ragrails.models.reranker.bm25:BM25Reranker",
    ),
    "voyage": _RerankerSpec(
        info=RerankerInfo(
            provider="voyage",
            default_model="rerank-2-lite",
            models=("rerank-2-lite", "rerank-2"),
        ),
        factory="ragrails.models.reranker.voyage:VoyageReranker",
    )
}


def list_rerankers() -> list[RerankerInfo]:
    return [spec.info for spec in RERANKER_SPECS.values()]


def register_reranker(
    provider: str,
    factory: RerankerFactory,
    *,
    default_model: str,
    models: tuple[str, ...] = (),
    replace: bool = False,
) -> None:
    if not provider:
        raise ValueError("provider is required")
    if provider in RERANKER_SPECS and not replace:
        raise ValueError(f"Reranker provider already registered: {provider!r}")

    RERANKER_SPECS[provider] = _RerankerSpec(
        info=RerankerInfo(provider=provider, default_model=default_model, models=models),
        factory=factory,
    )


def create_reranker(
    provider: str = "voyage",
    *,
    model: str | None = None,
    **options: Any,
) -> Reranker:
    if provider not in RERANKER_SPECS:
        available = ", ".join(sorted(RERANKER_SPECS))
        raise ValueError(f"Unknown reranker provider '{provider}'. Available providers: {available}")

    spec = RERANKER_SPECS[provider]
    factory = _load_factory(spec.factory)
    return factory(
        model_name=model or spec.info.default_model,
        **options,
    )


def _load_factory(factory: object) -> RerankerFactory:
    if callable(factory):
        return factory
    if not isinstance(factory, str):
        raise TypeError("reranker factory must be a callable or import path")

    module_name, class_name = factory.split(":", 1)
    module = import_module(module_name)
    return getattr(module, class_name)
