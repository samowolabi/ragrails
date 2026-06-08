"""REST services for retrieval."""

from __future__ import annotations

from typing import Any

from ragrails.interfaces.sdk import RagRails
from ragrails.interfaces.server.common import model_data, result_data

from .schemas import RetrieveRequest


def retrieve_chunks(request: RetrieveRequest) -> dict[str, Any]:
    data = model_data(request)
    query = data.pop("query")
    provider = data.pop("provider")
    model = data.pop("model")
    embedder_options = data.pop("embedder_options")
    vector_db = data.pop("vector_db")
    collection = data.pop("collection")
    url = data.pop("url")
    options = data.pop("options")
    reranker_provider = data.pop("reranker")
    reranker_model = data.pop("reranker_model")
    reranker_options = data.pop("reranker_options")
    use_rerank = data.get("use_rerank", False)
    rag = RagRails(
        collection=collection,
        vector_store={"provider": vector_db, "url": url, "options": options},
        embedding={"provider": provider, "model": model, "options": embedder_options},
        reranker={
            "enabled": use_rerank,
            "provider": reranker_provider,
            "model": reranker_model,
            "options": reranker_options,
        },
    )
    return result_data(rag.retrieve(query, **data))
