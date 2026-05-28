"""Compatibility exports for REST API schemas."""

from ragrails.interfaces.server.chunking.schemas import ChunkRequest, ChunkResponse
from ragrails.interfaces.server.embedding.schemas import EmbedRequest, EmbedResponse
from ragrails.interfaces.server.health import HealthResponse
from ragrails.interfaces.server.ingestion.schemas import (
    ApiIngestRequest,
    ApiIngestResponse,
    DocsIngestRequest,
    DocumentInput,
    ParseResponse,
    ScrapeResponse,
    UrlIngestRequest,
)
from ragrails.interfaces.server.retrieval.schemas import RetrievedChunkResponse, RetrieveRequest, RetrieveResponse
from ragrails.interfaces.server.storing.schemas import StoreRequest, StoreResponse

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
