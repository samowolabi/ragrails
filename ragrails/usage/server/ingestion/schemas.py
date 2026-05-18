"""REST schemas for ingestion."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class DocumentInput(BaseModel):
    filename: str
    title: str | None = None
    description: str | None = None


class ApiIngestRequest(BaseModel):
    url: str
    title: str = "API Response"
    description: str = ""
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "GET"
    headers: dict[str, Any] | None = None
    params: dict[str, Any] | None = None
    body: dict[str, Any] | None = None
    pagination: dict[str, Any] | None = None
    max_pages: int = 100
    output_dir: str = "files/output/api"
    frontmatter: bool = True


class UrlIngestRequest(BaseModel):
    url: str | list[str]
    mode: Literal["each", "full"] = "each"
    output_dir: str = "files/output/web_crawled"
    frontmatter: bool = True
    dlq_path: str | None = None
    max_depth: int = 3
    max_pages: int = 200


class DocsIngestRequest(BaseModel):
    files: str | list[str | DocumentInput] | None = None
    folder: str | None = None
    input_dir: str = "files/input"
    output_dir: str = "files/output/docs"
    frontmatter: bool = True


class ScrapeResponse(BaseModel):
    pages: int
    failed: int
    output_dir: str
    files: list[str]
    dlq_path: str
    errors: list[str]


class ParseResponse(BaseModel):
    documents: int
    failed: int
    output_dir: str
    files: list[str]
    errors: list[str]


class ApiIngestResponse(BaseModel):
    pages: int
    items: int
    failed: int
    output_dir: str
    files: list[str]
    errors: list[str]
