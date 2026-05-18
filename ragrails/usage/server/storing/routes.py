"""REST routes for storage."""

from __future__ import annotations

from fastapi import APIRouter

from . import services
from .schemas import StoreRequest, StoreResponse

router = APIRouter(prefix="/v1")


@router.post("/store", response_model=StoreResponse)
def store(request: StoreRequest) -> dict:
    return services.store_chunks(request)
