"""REST schemas for embedding."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class EmbedRequest(BaseModel):
    input_dir: str = "files/output/chunks"
    vector_db: Literal["qdrant", "pinecone", "weaviate"] = "qdrant"
    collection: str | None = None
    url: str | None = None
    files: str | list[str] | None = None
    batch_size: int = 64
    embedder: str = "voyage"
    model: str = "voyage-3"


class EmbedResponse(BaseModel):
    files: int
    chunks: int
    input_dir: str
    provider: str
    collection: str
    errors: list[str]
