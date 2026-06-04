"""REST services for chunking."""

from __future__ import annotations

from typing import Any

from ragrails.interfaces.sdk import RagRails
from ragrails.interfaces.server.common import model_data, result_data

from .schemas import ChunkRequest


def chunk_dir(request: ChunkRequest) -> dict[str, Any]:
    return result_data(RagRails().chunk(**model_data(request)))
