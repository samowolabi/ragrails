"""REST services for SDK pipeline helpers."""

from __future__ import annotations

from typing import Any

from ragrails.interfaces.sdk import RagRails
from ragrails.interfaces.server.common import model_data, result_data

from .schemas import PipelineIngestRequest, PipelineQueryRequest


def ingest_pipeline(request: PipelineIngestRequest) -> dict[str, Any]:
    data = model_data(request)
    embedding = data.get("embedding") or {}
    storage = data.get("storage") or {}
    rag = RagRails(
        collection=storage.get("collection"),
        vector_store={
            "provider": storage.get("vector_db") or storage.get("provider"),
            "url": storage.get("url"),
            "options": storage.get("options"),
        },
        embedding={
            "provider": embedding.get("provider"),
            "model": embedding.get("model"),
            "options": embedding.get("options"),
        },
    )
    data["embedding"] = {key: value for key, value in embedding.items() if key not in {"provider", "model", "options"}}
    data["storage"] = {key: value for key, value in storage.items() if key not in {"vector_db", "provider", "collection", "url", "options"}}
    return result_data(rag.ingest(**data))


def query_pipeline(request: PipelineQueryRequest) -> dict[str, Any]:
    data = model_data(request)
    query = data.pop("query")
    embedding = data.get("embedding") or {}
    retrieval = data.get("retrieval") or {}
    rerank = retrieval.get("rerank") or {}
    rag = RagRails(
        collection=retrieval.get("collection"),
        vector_store={
            "provider": retrieval.get("vector_db") or retrieval.get("provider"),
            "url": retrieval.get("url"),
            "options": retrieval.get("options"),
        },
        embedding={
            "provider": embedding.get("provider"),
            "model": embedding.get("model"),
            "options": embedding.get("options"),
        },
        reranker={
            "enabled": rerank.get("enabled", False) if isinstance(rerank, dict) else False,
            "provider": rerank.get("provider") if isinstance(rerank, dict) else None,
            "model": rerank.get("model") if isinstance(rerank, dict) else None,
            "options": rerank.get("options") if isinstance(rerank, dict) else None,
        },
    )
    data["embedding"] = {key: value for key, value in embedding.items() if key not in {"provider", "model", "options"}}
    data["retrieval"] = {key: value for key, value in retrieval.items() if key not in {"vector_db", "provider", "collection", "url", "options"}}
    if isinstance(data["retrieval"].get("rerank"), dict):
        data["retrieval"]["rerank"] = {
            key: value
            for key, value in data["retrieval"]["rerank"].items()
            if key not in {"provider", "model", "options"}
        }
    return result_data(rag.query(query, **data))
