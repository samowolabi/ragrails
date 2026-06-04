"""REST schemas for SDK pipeline helpers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ragrails.interfaces.server.retrieval.schemas import RetrieveResponse


class PipelineIngestRequest(BaseModel):
    docs: str | list[str | dict[str, Any]] | dict[str, Any] | None = None
    urls: str | list[str | dict[str, Any]] | dict[str, Any] | None = None
    api: str | list[str | dict[str, Any]] | dict[str, Any] | None = None
    markdown: str | list[str | dict[str, Any]] | None = None
    ingestion: dict[str, Any] | None = None
    chunking: dict[str, Any] | None = None
    embedding: dict[str, Any] | None = None
    storage: dict[str, Any] | None = None


class PipelineIngestResponse(BaseModel):
    sources: int
    chunks: int
    embedded: int
    stored: int
    source_results: dict[str, Any]
    chunk_result: dict[str, Any]
    embed_result: dict[str, Any]
    store_result: dict[str, Any]
    failed: int
    errors: list[dict[str, Any]]


class PipelineQueryRequest(BaseModel):
    query: str
    embedding: dict[str, Any] | None = None
    retrieval: dict[str, Any] | None = None


PipelineQueryResponse = RetrieveResponse
