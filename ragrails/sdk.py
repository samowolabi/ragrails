"""Class-based SDK entrypoint for Ragrails."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from rag.stg_01_ingestors.api import ingest_api as _ingest_api
from rag.stg_01_ingestors.config import ApiIngestorConfig, DocsIngestorConfig, UrlIngestorConfig
from rag.stg_01_ingestors.docs import ingest_docs as _ingest_docs
from rag.stg_01_ingestors.url import scrape_url

from .types import ApiIngestResult, ParseResult, ScrapeResult


SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".csv",
    ".docx",
    ".html",
    ".htm",
    ".md",
    ".pdf",
    ".pptx",
    ".txt",
    ".xlsx",
}


class RagRails:
    """Main public SDK client.

    Example:
        from ragrails import RagRails

        result = RagRails().scrape(
            url=["https://example.com/docs"],
            mode="full",
            output_dir="files/output/web_crawled",
        )
    """

    def scrape(
        self,
        url: str | list[str],
        *,
        mode: Literal["each", "full"] = "each",
        output_dir: str = "files/output/web_crawled",
        frontmatter: bool = True,
        dlq_path: str = "files/output/dlq.json",
        max_depth: int = 3,
        max_pages: int = 200,
    ) -> ScrapeResult:
        """Scrape exact URLs or crawl a full site into markdown files."""
        self._validate_scrape_args(
            url=url,
            mode=mode,
            output_dir=output_dir,
            dlq_path=dlq_path,
            max_depth=max_depth,
            max_pages=max_pages,
        )

        config = UrlIngestorConfig(
            output_dir=output_dir,
            dlq_path=dlq_path,
            max_depth=max_depth,
            max_pages=max_pages,
        )
        stats = asyncio.run(
            scrape_url(
                urls=url,
                mode=mode,
                config=config,
                frontmatter=frontmatter,
            )
        )
        return ScrapeResult(
            pages=stats["pages"],
            failed=stats["failed"],
            output_dir=output_dir,
            files=stats.get("files", []),
            dlq_path=dlq_path,
            errors=stats.get("errors", []),
        )

    @staticmethod
    def _validate_scrape_args(
        *,
        url: str | list[str],
        mode: str,
        output_dir: str,
        dlq_path: str,
        max_depth: int,
        max_pages: int,
    ) -> None:
        if mode not in {"each", "full"}:
            raise ValueError(f"Invalid mode '{mode}' — use 'each' or 'full'")
        if not output_dir:
            raise ValueError("output_dir is required")
        if not dlq_path:
            raise ValueError("dlq_path is required")
        if max_depth < 0:
            raise ValueError("max_depth must be greater than or equal to 0")
        if max_pages < 1:
            raise ValueError("max_pages must be greater than 0")

        urls = [url] if isinstance(url, str) else list(url)
        if not urls:
            raise ValueError("url must include at least one URL")

        for item in urls:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("url values must be non-empty strings")
            parsed = urlparse(item)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Invalid URL '{item}' — use an absolute http(s) URL")

    def parse(
        self,
        files: str | list[str | dict] | None = None,
        *,
        folder: str | None = None,
        input_dir: str = "files/input",
        output_dir: str = "files/output/docs",
        frontmatter: bool = True,
    ) -> ParseResult:
        """Convert local documents into markdown files.

        `files` can be a single filename, a list of filenames, or dicts with
        `filename`, `title`, and `description` for custom metadata.
        `folder` converts all supported files in that folder.
        """
        self._validate_parse_args(
            files=files,
            folder=folder,
            input_dir=input_dir,
            output_dir=output_dir,
        )

        docs_input = self._discover_docs(folder) if folder else files
        docs = self._normalize_docs(docs_input)
        config = DocsIngestorConfig(
            input_dir=folder or input_dir,
            output_dir=output_dir,
        )
        stats = _ingest_docs(docs=docs, config=config, frontmatter=frontmatter)
        return ParseResult(
            documents=stats["documents"],
            failed=stats["failed"],
            output_dir=output_dir,
            files=stats["files"],
            errors=stats.get("errors", []),
        )

    @staticmethod
    def _validate_parse_args(
        *,
        files: str | list[str | dict] | None,
        folder: str | None,
        input_dir: str,
        output_dir: str,
    ) -> None:
        if files is None and folder is None:
            raise ValueError("Provide either 'files' or 'folder'")
        if files is not None and folder is not None:
            raise ValueError("Provide either 'files' or 'folder', not both")
        if not output_dir:
            raise ValueError("output_dir is required")
        if folder is None and not input_dir:
            raise ValueError("input_dir is required when using files")

    def fetch(
        self,
        url: str,
        *,
        title: str = "API Response",
        description: str = "",
        method: str = "GET",
        headers: dict | None = None,
        params: dict | None = None,
        body: dict | None = None,
        pagination: dict | None = None,
        max_pages: int = 100,
        output_dir: str = "files/output/api",
        frontmatter: bool = True,
    ) -> ApiIngestResult:
        """Fetch a REST API endpoint and save response pages as markdown."""
        self._validate_fetch_args(
            url=url,
            method=method,
            headers=headers,
            params=params,
            body=body,
            pagination=pagination,
            max_pages=max_pages,
            output_dir=output_dir,
        )

        config = ApiIngestorConfig(output_dir=output_dir, max_pages=max_pages)
        stats = asyncio.run(
            _ingest_api(
                url=url,
                title=title,
                description=description,
                method=method,
                headers=headers,
                params=params,
                body=body,
                pagination=pagination,
                max_pages=max_pages,
                config=config,
                frontmatter=frontmatter,
            )
        )
        return ApiIngestResult(
            pages=stats["pages"],
            items=stats["items"],
            failed=stats["failed"],
            output_dir=output_dir,
            files=stats["files"],
            errors=stats.get("errors", []),
        )

    @staticmethod
    def _validate_fetch_args(
        *,
        url: str,
        method: str,
        headers: dict | None,
        params: dict | None,
        body: dict | None,
        pagination: dict | None,
        max_pages: int,
        output_dir: str,
    ) -> None:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url must be a non-empty string")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Invalid URL '{url}' — use an absolute http(s) URL")

        allowed_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
        if method.upper() not in allowed_methods:
            allowed = ", ".join(sorted(allowed_methods))
            raise ValueError(f"Invalid method '{method}' — use one of: {allowed}")
        if not output_dir:
            raise ValueError("output_dir is required")
        if max_pages < 1:
            raise ValueError("max_pages must be greater than 0")

        for name, value in {
            "headers": headers,
            "params": params,
            "body": body,
            "pagination": pagination,
        }.items():
            if value is not None and not isinstance(value, dict):
                raise ValueError(f"{name} must be a dict when provided")

    @staticmethod
    def _discover_docs(folder: str) -> list[str]:
        base = Path(folder)
        if not folder:
            raise ValueError("folder is required")
        if not base.exists():
            raise FileNotFoundError(f"Document folder not found: {folder}")
        if not base.is_dir():
            raise NotADirectoryError(f"Document folder is not a directory: {folder}")

        files = [
            path.name
            for path in sorted(base.iterdir())
            if path.is_file() and path.suffix.lower() in SUPPORTED_DOCUMENT_EXTENSIONS
        ]
        if not files:
            raise ValueError(f"No supported document files found in folder: {folder}")
        return files

    @staticmethod
    def _normalize_docs(files: str | list[str | dict]) -> list[dict]:
        file_list = [files] if isinstance(files, str) else list(files)
        if not file_list:
            raise ValueError("files must include at least one document")

        docs = []
        for item in file_list:
            if isinstance(item, str):
                if not item.strip():
                    raise ValueError("file names must be non-empty strings")
                RagRails._validate_document_extension(item)
                stem = item.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                docs.append({"filename": item, "title": stem, "description": ""})
            else:
                filename = item.get("filename") or item.get("file")
                if not filename:
                    raise ValueError("Document dicts must include 'filename' or 'file'")
                if not isinstance(filename, str) or not filename.strip():
                    raise ValueError("Document filename values must be non-empty strings")
                RagRails._validate_document_extension(filename)
                stem = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                docs.append({
                    "filename": filename,
                    "title": item.get("title") or stem,
                    "description": item.get("description", ""),
                })
        return docs

    @staticmethod
    def _validate_document_extension(filename: str) -> None:
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
            allowed = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
            raise ValueError(f"Unsupported document type '{suffix}' for '{filename}'. Supported extensions: {allowed}")
