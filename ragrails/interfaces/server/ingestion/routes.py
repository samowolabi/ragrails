"""REST routes for ingestion."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from ragrails.interfaces.server.common import sse_frame
from . import services
from .schemas import ApiIngestRequest, ApiIngestResponse, DocsIngestRequest, ParseResponse, ScrapeResponse, UrlIngestRequest

router = APIRouter(prefix="/v1")


@router.post("/ingest/api", response_model=ApiIngestResponse)
def ingest_api(request: ApiIngestRequest) -> dict:
    return services.fetch_api(request)


@router.post("/ingest/url", response_model=ScrapeResponse)
def ingest_url(request: UrlIngestRequest) -> dict:
    return services.scrape_url(request)


@router.post("/ingest/url/stream")
def ingest_url_stream(request: UrlIngestRequest):
    return StreamingResponse(
        (sse_frame(event) for event in services.scrape_url_stream(request)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/ingest/docs", response_model=ParseResponse)
def ingest_docs(request: DocsIngestRequest) -> dict:
    return services.parse_docs(request)


@router.post("/ingest/docs/upload", response_model=ParseResponse)
async def upload_docs(
    files: list[UploadFile] = File(...),
    frontmatter: bool = Form(False),
    title: str | None = Form(None),
    description: str = Form(""),
) -> dict:
    uploaded = []
    for file in files:
        content = await file.read()
        filename = file.filename or "upload"
        uploaded.append({
            "content": content,
            "filename": filename,
            "title": title if title and len(files) == 1 else None,
            "description": description,
            "content_type": file.content_type,
            "source": filename,
        })
    return services.parse_uploaded_docs(uploaded, frontmatter=frontmatter)
