"""REST services for storage."""

from __future__ import annotations

from typing import Any

from ragrails.interfaces.sdk import RagRails
from ragrails.interfaces.server.common import model_data, result_data

from .schemas import DeleteRequest, EditRequest, StoreRequest


def store_chunks(request: StoreRequest) -> dict[str, Any]:
    return result_data(RagRails().store(**model_data(request)))


def edit_chunks(request: EditRequest) -> dict[str, Any]:
    data = model_data(request)
    chunks = data.pop("chunks")
    provider = data.pop("provider")
    model = data.pop("model")
    embedder_options = data.pop("embedder_options")
    embedder = RagRails().embedder(provider=provider, model=model, input_type="document", options=embedder_options)
    return result_data(RagRails().edit(chunks=chunks, embedder=embedder, **data))


def delete_chunks(request: DeleteRequest) -> dict[str, Any]:
    return result_data(RagRails().delete(**model_data(request)))
