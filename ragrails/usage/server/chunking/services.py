"""REST services for chunking."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ragrails import RagRails
from ragrails.usage.server.common import model_data

from .schemas import ChunkRequest


def chunk_dir(request: ChunkRequest) -> dict[str, Any]:
    return asdict(RagRails().chunk(**model_data(request)))
