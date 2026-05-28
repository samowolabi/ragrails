"""Health check route."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str


router = APIRouter(prefix="/v1")


@router.get("/health", response_model=HealthResponse)
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ragrails"}
