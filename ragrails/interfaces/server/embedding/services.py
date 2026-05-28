"""REST services for embedding."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ragrails import RagRails
from ragrails.interfaces.server.common import model_data

from .schemas import EmbedRequest


def embed_chunks(request: EmbedRequest) -> dict[str, Any]:
    return asdict(RagRails().embed(**model_data(request)))
