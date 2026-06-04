"""Compatibility exports for REST API schemas."""

from ragrails.interfaces.server.chunking.schemas import ChunkRequest, ChunkResponse
from ragrails.interfaces.server.chat.schemas import ChatRequest, ChatResponse
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
from ragrails.interfaces.server.pipeline.schemas import PipelineIngestRequest, PipelineIngestResponse, PipelineQueryRequest, PipelineQueryResponse
from ragrails.interfaces.server.storing.schemas import DeleteRequest, DeleteResponse, EditRequest, EditResponse, StoreRequest, StoreResponse

__all__ = [
    "ApiIngestRequest",
    "ApiIngestResponse",
    "ChunkRequest",
    "ChunkResponse",
    "ChatRequest",
    "ChatResponse",
    "DeleteRequest",
    "DeleteResponse",
    "DocsIngestRequest",
    "DocumentInput",
    "EditRequest",
    "EditResponse",
    "EmbedRequest",
    "EmbedResponse",
    "HealthResponse",
    "ParseResponse",
    "PipelineIngestRequest",
    "PipelineIngestResponse",
    "PipelineQueryRequest",
    "PipelineQueryResponse",
    "RetrievedChunkResponse",
    "RetrieveRequest",
    "RetrieveResponse",
    "ScrapeResponse",
    "StoreRequest",
    "StoreResponse",
    "UrlIngestRequest",
]
