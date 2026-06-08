"""REST schemas for storage."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class StoreRequest(BaseModel):
    embedded_chunks: list[dict]
    vector_db: Literal["qdrant", "qdrant_cloud", "pinecone", "weaviate"] = "qdrant"
    collection: str | None = None
    url: str | None = None
    batch_size: int = 64
    ensure_collection: bool = True
    options: dict | None = None


class StoreResponse(BaseModel):
    inputs: int
    stored: int
    items: list[dict]
    failed: int
    provider: str
    collection: str
    errors: list[dict]


class EditRequest(BaseModel):
    chunks: list[dict]
    provider: str = "voyage"
    model: str = "voyage-3"
    embedder_options: dict | None = None
    vector_db: Literal["qdrant", "qdrant_cloud", "pinecone", "weaviate"] = "qdrant"
    collection: str | None = None
    url: str | None = None
    batch_size: int = 64
    options: dict | None = None


class EditResponse(BaseModel):
    requested: int
    edited: int
    items: list[dict]
    failed: int
    provider: str
    collection: str
    errors: list[dict]


class DeleteRequest(BaseModel):
    ids: list[str]
    vector_db: Literal["qdrant", "qdrant_cloud", "pinecone", "weaviate"] = "qdrant"
    collection: str | None = None
    url: str | None = None
    options: dict | None = None


class DeleteResponse(BaseModel):
    requested: int
    deleted: int
    items: list[dict]
    failed: int
    provider: str
    collection: str
    errors: list[dict]

__all__ = ["DeleteRequest", "DeleteResponse", "EditRequest", "EditResponse", "StoreRequest", "StoreResponse"]
