"""REST routes for ingestion."""

from __future__ import annotations

from fastapi import APIRouter

from . import services
from .schemas import ApiIngestRequest, ApiIngestResponse, DocsIngestRequest, ParseResponse, ScrapeResponse, UrlIngestRequest

router = APIRouter(prefix="/v1")


@router.post("/ingest/api", response_model=ApiIngestResponse)
def ingest_api(request: ApiIngestRequest) -> dict:
    return services.fetch_api(request)


@router.post("/ingest/url", response_model=ScrapeResponse)
def ingest_url(request: UrlIngestRequest) -> dict:
    return services.scrape_url(request)


@router.post("/ingest/docs", response_model=ParseResponse)
def ingest_docs(request: DocsIngestRequest) -> dict:
    return services.parse_docs(request)
