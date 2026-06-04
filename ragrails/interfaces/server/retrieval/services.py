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
    reranker_provider = data.pop("reranker")
    reranker_model = data.pop("reranker_model")
    reranker_options = data.pop("reranker_options")
    use_rerank = data.get("use_rerank", False)
    rag = RagRails()
    embedder = rag.embedder(provider=provider, model=model, input_type="query", options=embedder_options)
    reranker = rag.reranker(provider=reranker_provider, model=reranker_model, options=reranker_options) if use_rerank else None
    return result_data(RagRails().retrieve(query, embedder=embedder, reranker=reranker, **data))
