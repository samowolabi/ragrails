"""REST routes for storage."""

from __future__ import annotations

from fastapi import APIRouter

from . import services
from .schemas import DeleteRequest, DeleteResponse, EditRequest, EditResponse, StoreRequest, StoreResponse

router = APIRouter(prefix="/v1")


@router.post("/store", response_model=StoreResponse)
def store(request: StoreRequest) -> dict:
    return services.store_chunks(request)


@router.post("/edit", response_model=EditResponse)
def edit(request: EditRequest) -> dict:
    return services.edit_chunks(request)


@router.post("/delete", response_model=DeleteResponse)
def delete(request: DeleteRequest) -> dict:
    return services.delete_chunks(request)
