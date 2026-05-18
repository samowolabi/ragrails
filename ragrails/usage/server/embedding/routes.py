"""REST routes for embedding."""

from __future__ import annotations

from fastapi import APIRouter

from . import services
from .schemas import EmbedRequest, EmbedResponse

router = APIRouter(prefix="/v1")


@router.post("/embed", response_model=EmbedResponse)
def embed(request: EmbedRequest) -> dict:
    return services.embed_chunks(request)
