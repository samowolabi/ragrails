"""REST routes for retrieval."""

from __future__ import annotations

from fastapi import APIRouter

from . import services
from .schemas import RetrieveRequest, RetrieveResponse

router = APIRouter(prefix="/v1")


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve(request: RetrieveRequest) -> dict:
    return services.retrieve_chunks(request)
