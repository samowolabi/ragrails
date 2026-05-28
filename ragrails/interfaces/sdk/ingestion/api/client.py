"""SDK methods for API ingestion."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from ragrails.types import ApiIngestResult
from ragrails.interfaces.sdk.shared import missing_extra, run_async
from ragrails.interfaces.sdk.ingestion.utils.shared import save_outputs_to_dir
from ragrails.interfaces.sdk.ingestion.utils.frontmatter import with_frontmatter


class ApiMixin:
    def fetch(
        self,
        url: str | None = None,
        *,
        title: str | None = None,
        description: str = "",
        method: str = "GET",
        headers: dict | None = None,
        params: dict | None = None,
        body: dict | None = None,
        pagination: dict | None = None,
        max_pages: int = 100,
        timeout: float | None = None,
        apis: list[str | dict] | None = None,
        frontmatter: bool = False,
        output_format: Literal["markdown", "json"] = "markdown",
        output_dest: Literal["response", "file"] = "response",
        output_dir: str | None = None,
    ) -> ApiIngestResult:
        """Fetch one or more REST API endpoints and return response pages as documents.

        Pass a single ``url`` or a batch of endpoints via ``apis``.

        The default behavior is response-only: outputs are returned in memory
        and no markdown/JSON files are written. Use ``output_dest="file"``
        with ``output_dir`` only when you explicitly want SDK convenience file
        output. ``frontmatter=True`` is also an SDK convenience and only
        modifies markdown text returned or saved by this method.

        ``output_format``: ``"markdown"`` (default) or ``"json"``.
        ``output_dest``: ``"response"`` (default) or ``"file"``.

        Example::

            result = rag.fetch("https://api.example.com/posts")

            result = rag.fetch(
                "https://api.example.com/posts",
                headers={"Authorization": "Bearer token"},
                pagination={"type": "page", "param": "page"},
                max_pages=10,
            )

            result = rag.fetch(apis=[
                "https://api.example.com/posts",
                {"url": "https://api.example.com/users", "title": "Users"},
            ])

            rag.fetch("https://api.example.com/posts", output_dest="file", output_dir="files/output/api")
        """
        self._validate_fetch_args(
            url=url,
            apis=apis,
            method=method,
            headers=headers,
            params=params,
            body=body,
            pagination=pagination,
            max_pages=max_pages,
            output_format=output_format,
            output_dest=output_dest,
            output_dir=output_dir,
        )

        try:
            from ragrails.core.stg_01_ingestors.api import ingest_api as _ingest_api
        except ImportError as exc:
            raise RuntimeError("API ingestion dependencies are missing. Reinstall with: pip install -U ragrails") from exc

        stats = run_async(
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
                timeout=timeout,
                apis=apis,
            )
        )

        outputs = stats.get("outputs", [])
        if frontmatter and output_format == "markdown":
            outputs = with_frontmatter(outputs)
        if output_dest == "file":
            outputs = save_outputs_to_dir(outputs, output_dir, output_format)

        return ApiIngestResult(
            documents=stats.get("documents", 0),
            failed=stats["failed"],
            outputs=outputs,
            errors=stats.get("errors", []),
        )

    @staticmethod
    def _validate_fetch_args(
        *,
        url: str | None,
        apis: list[str | dict] | None,
        method: str,
        headers: dict | None,
        params: dict | None,
        body: dict | None,
        pagination: dict | None,
        max_pages: int,
        output_format: str,
        output_dest: str,
        output_dir: str | None,
    ) -> None:
        if url is None and not apis:
            raise ValueError("Provide either 'url' or 'apis'")
        if url is not None and apis is not None:
            raise ValueError("Provide either 'url' or 'apis', not both")

        if url is not None:
            if not isinstance(url, str) or not url.strip():
                raise ValueError("url must be a non-empty string")
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Invalid URL '{url}' — use an absolute http(s) URL")

        allowed_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
        if method.upper() not in allowed_methods:
            allowed = ", ".join(sorted(allowed_methods))
            raise ValueError(f"Invalid method '{method}' — use one of: {allowed}")
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

        if output_format not in {"markdown", "json"}:
            raise ValueError(f"Invalid output_format '{output_format}' — use 'markdown' or 'json'")
        if output_dest not in {"response", "file"}:
            raise ValueError(f"Invalid output_dest '{output_dest}' — use 'response' or 'file'")
        if output_dest == "file" and not output_dir:
            raise ValueError("output_dir is required when output_dest is 'file'")
