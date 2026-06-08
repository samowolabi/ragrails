"""REST services for storage."""

from __future__ import annotations

from typing import Any

from ragrails.interfaces.sdk import RagRails
from ragrails.interfaces.server.common import model_data, result_data

from .schemas import DeleteRequest, EditRequest, StoreRequest


def store_chunks(request: StoreRequest) -> dict[str, Any]:
    data = model_data(request)
    embedded_chunks = data.pop("embedded_chunks")
    vector_db = data.pop("vector_db")
    collection = data.pop("collection")
    url = data.pop("url")
    options = data.pop("options")
    rag = RagRails(collection=collection, vector_store={"provider": vector_db, "url": url, "options": options})
    return result_data(rag.store(embedded_chunks=embedded_chunks, **data))


def edit_chunks(request: EditRequest) -> dict[str, Any]:
    data = model_data(request)
    chunks = data.pop("chunks")
    provider = data.pop("provider")
    model = data.pop("model")
    embedder_options = data.pop("embedder_options")
    vector_db = data.pop("vector_db")
    collection = data.pop("collection")
    url = data.pop("url")
    options = data.pop("options")
    rag = RagRails(
        collection=collection,
        vector_store={"provider": vector_db, "url": url, "options": options},
        embedding={"provider": provider, "model": model, "options": embedder_options},
    )
    return result_data(rag.edit(chunks=chunks, **data))


def delete_chunks(request: DeleteRequest) -> dict[str, Any]:
    data = model_data(request)
    ids = data.pop("ids")
    vector_db = data.pop("vector_db")
    collection = data.pop("collection")
    url = data.pop("url")
    options = data.pop("options")
    rag = RagRails(collection=collection, vector_store={"provider": vector_db, "url": url, "options": options})
    return result_data(rag.delete(ids=ids))
