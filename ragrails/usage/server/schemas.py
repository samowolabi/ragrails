"""Compatibility exports for REST API schemas."""

from ragrails.usage.server.chunking.schemas import ChunkRequest, ChunkResponse
from ragrails.usage.server.embedding.schemas import EmbedRequest, EmbedResponse
from ragrails.usage.server.health import HealthResponse
from ragrails.usage.server.ingestion.schemas import (
    ApiIngestRequest,
    ApiIngestResponse,
    DocsIngestRequest,
    DocumentInput,
    ParseResponse,
    ScrapeResponse,
    UrlIngestRequest,
)
from ragrails.usage.server.retrieval.schemas import RetrievedChunkResponse, RetrieveRequest, RetrieveResponse
from ragrails.usage.server.storing.schemas import StoreRequest, StoreResponse

__all__ = [
    "ApiIngestRequest",
    "ApiIngestResponse",
    "ChunkRequest",
    "ChunkResponse",
    "DocsIngestRequest",
    "DocumentInput",
    "EmbedRequest",
    "EmbedResponse",
    "HealthResponse",
    "ParseResponse",
    "RetrievedChunkResponse",
    "RetrieveRequest",
    "RetrieveResponse",
    "ScrapeResponse",
    "StoreRequest",
    "StoreResponse",
    "UrlIngestRequest",
]
