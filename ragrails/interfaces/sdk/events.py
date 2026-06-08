"""SDK streaming event helpers."""

from __future__ import annotations

from typing import Any


def stream_event(
    event_type: str,
    *,
    stage: str,
    sequence: int,
    message: str = "",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "type": event_type,
        "stage": stage,
        "message": message,
        "data": data or {},
        "sequence": sequence,
    }
