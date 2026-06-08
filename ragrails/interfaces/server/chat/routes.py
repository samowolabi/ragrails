"""REST routes for chat."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from ragrails.interfaces.server.common import sse_frame
from . import services
from .schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/v1")


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> dict:
    return services.run_chat(request)


@router.post("/chat/stream")
def chat_stream(request: ChatRequest):
    return StreamingResponse(
        (sse_frame(event) for event in services.run_chat_stream(request)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
