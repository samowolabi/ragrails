"""Shared helpers for REST API modules."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any


def model_data(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def result_data(result: Any) -> dict[str, Any]:
    if is_dataclass(result):
        return asdict(result)
    if isinstance(result, dict):
        return result
    raise TypeError(f"Unsupported REST result type: {type(result).__name__}")


def sse_frame(event: dict[str, Any]) -> str:
    event_type = event.get("type", "message")
    return f"event: {event_type}\ndata: {json.dumps(event, default=str)}\n\n"
