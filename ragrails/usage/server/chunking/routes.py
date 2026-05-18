"""REST routes for chunking."""

from __future__ import annotations

from fastapi import APIRouter

from . import services
from .schemas import ChunkRequest, ChunkResponse

router = APIRouter(prefix="/v1")


@router.post("/chunk", response_model=ChunkResponse)
def chunk(request: ChunkRequest) -> dict:
    return services.chunk_dir(request)
