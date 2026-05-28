"""Shared helpers for REST API modules."""

from __future__ import annotations

from typing import Any


def model_data(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
