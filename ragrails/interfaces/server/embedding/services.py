"""REST services for embedding."""

from __future__ import annotations

from typing import Any

from ragrails.interfaces.sdk import RagRails
from ragrails.interfaces.server.common import model_data, result_data

from .schemas import EmbedRequest


def embed_chunks(request: EmbedRequest) -> dict[str, Any]:
    data = model_data(request)
    chunks = data.pop("chunks")
    batch_size = data.pop("batch_size")
    input_type = data.pop("input_type")
    rag = RagRails(embedding=data)
    return result_data(rag.embed(chunks=chunks, input_type=input_type, batch_size=batch_size))
