"""REST schemas for chunking."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ChunkRequest(BaseModel):
    markdown: str | list[str | dict[str, Any]]
    title: str = ""
    source: str = ""
    chunk_size: int = 2000
    chunk_overlap: int = 200
    min_chunk_length: int = 100


class ChunkResponse(BaseModel):
    inputs: int
    chunks: int
    items: list[dict]
    failed: int
    errors: list[str]
