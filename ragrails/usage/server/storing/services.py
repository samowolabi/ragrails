"""REST services for storage."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ragrails import RagRails
from ragrails.usage.server.common import model_data

from .schemas import StoreRequest


def store_chunks(request: StoreRequest) -> dict[str, Any]:
    return asdict(RagRails().store(**model_data(request)))
