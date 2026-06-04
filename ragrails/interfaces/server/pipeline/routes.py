"""REST routes for SDK pipeline helpers."""

from __future__ import annotations

from fastapi import APIRouter

from . import services
from .schemas import PipelineIngestRequest, PipelineIngestResponse, PipelineQueryRequest, PipelineQueryResponse

router = APIRouter(prefix="/v1")


@router.post("/pipelines/ingest", response_model=PipelineIngestResponse)
def ingest(request: PipelineIngestRequest) -> dict:
    return services.ingest_pipeline(request)


@router.post("/pipelines/query", response_model=PipelineQueryResponse)
def query(request: PipelineQueryRequest) -> dict:
    return services.query_pipeline(request)
