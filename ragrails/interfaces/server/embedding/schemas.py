"""REST schemas for embedding."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class EmbedRequest(BaseModel):
    chunks: list[dict]
    provider: str = "voyage"
    model: str = "voyage-3"
    input_type: str = "document"
    batch_size: int = 64
    options: dict | None = None


class EmbedResponse(BaseModel):
    inputs: int
    embedded: int
    items: list[dict]
    failed: int
    errors: list[dict]
