"""REST schemas for ingestion."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class DocumentInput(BaseModel):
    path: str | None = None
    content: bytes | None = None
    filename: str | None = None
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
    timeout: float | None = None
    apis: list[str | dict[str, Any]] | None = None
    frontmatter: bool = False


class UrlIngestRequest(BaseModel):
    url: str | list[str | dict[str, Any]]
    mode: Literal["each", "full"] = "each"
    frontmatter: bool = False
    max_depth: int = 3
    max_pages: int = 200
    verbose: bool = False


class DocsIngestRequest(BaseModel):
    files: str | list[str | DocumentInput] | None = None
    folder: str | None = None
    frontmatter: bool = False


class ScrapeResponse(BaseModel):
    pages: int
    failed: int
    outputs: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    dlq: dict[str, Any] | None = None


class ParseResponse(BaseModel):
    documents: int
    failed: int
    outputs: list[dict[str, Any]]
    errors: list[dict[str, Any]]


class ApiIngestResponse(BaseModel):
    documents: int
    failed: int
    outputs: list[dict[str, Any]]
    errors: list[dict[str, Any]]
