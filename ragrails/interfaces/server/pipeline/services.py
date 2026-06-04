"""REST services for SDK pipeline helpers."""

from __future__ import annotations

from typing import Any

from ragrails.interfaces.sdk import RagRails
from ragrails.interfaces.server.common import model_data, result_data

from .schemas import PipelineIngestRequest, PipelineQueryRequest


def ingest_pipeline(request: PipelineIngestRequest) -> dict[str, Any]:
    return result_data(RagRails().ingest(**model_data(request)))


def query_pipeline(request: PipelineQueryRequest) -> dict[str, Any]:
    data = model_data(request)
    query = data.pop("query")
    return result_data(RagRails().query(query, **data))
