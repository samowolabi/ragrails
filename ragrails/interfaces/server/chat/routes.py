"""REST routes for chat."""

from __future__ import annotations

from fastapi import APIRouter

from . import services
from .schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/v1")


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> dict:
    return services.run_chat(request)
