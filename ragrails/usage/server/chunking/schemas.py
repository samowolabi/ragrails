"""REST schemas for chunking."""

from __future__ import annotations

from pydantic import BaseModel


class ChunkRequest(BaseModel):
    input_dir: str = "files/output/web_crawled"
    output_dir: str = "files/output/chunks"
    chunk_size: int = 2000
    chunk_overlap: int = 200
    min_chunk_length: int = 100


class ChunkResponse(BaseModel):
    files: int
    chunks: int
    output_dir: str
    output_files: list[str]
    failed: int
    errors: list[str]
