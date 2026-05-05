"""Public SDK result types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScrapeResult:
    """Summary returned by `RagRails().scrape(...)`."""

    pages: int
    failed: int
    output_dir: str
    files: list[str]
    dlq_path: str
    errors: list[str]


@dataclass(frozen=True)
class ParseResult:
    """Summary returned by `RagRails().parse(...)`."""

    documents: int
    failed: int
    output_dir: str
    files: list[str]
    errors: list[str]


@dataclass(frozen=True)
class ApiIngestResult:
    """Summary returned by `RagRails().fetch(...)`."""

    pages: int
    items: int
    failed: int
    output_dir: str
    files: list[str]
    errors: list[str]
