"""SDK methods for URL ingestion."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from ragrails.types import DLQ, ScrapeResult
from ragrails.interfaces.sdk.shared import missing_extra, run_async
from ragrails.interfaces.sdk.ingestion.utils.shared import save_outputs_to_dir
from ragrails.interfaces.sdk.ingestion.utils.frontmatter import with_frontmatter


class UrlMixin:
    def setup_url(self, *, browser: str = "chromium") -> dict:
        """Install the Playwright browser binary needed by URL ingestion.

        Example::

            rag.setup_url()
            rag.setup_url(browser="firefox")
        """
        if not browser or not browser.strip():
            raise ValueError("browser is required")

        try:
            import playwright  # noqa: F401
        except ImportError as exc:
            raise missing_extra("URL setup", "url", exc)

        command = [sys.executable, "-m", "playwright", "install", browser]
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            details = _setup_error_details(completed)
            raise RuntimeError(
                "Failed to install Playwright browser binary. "
                f"Run manually: {' '.join(command)}"
                f"{details}"
            )

        return {
            "browser": browser,
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    def scrape(
        self,
        url: str | list[str | dict] | None = None,
        *,
        mode: Literal["each", "full"] = "each",
        max_depth: int = 3,
        max_pages: int = 200,
        verbose: bool = False,
        frontmatter: bool = False,
        output_format: Literal["markdown", "json"] = "markdown",
        output_dest: Literal["response", "file"] = "response",
        output_dir: str | None = None,
        dlq: DLQ | str | None = None,
    ) -> ScrapeResult:
        """Scrape exact URLs or crawl full sites and return pages as documents.

        ``url`` can be a single URL string, a list of URL strings, or a list
        of dicts for per-URL config: ``{"url": ..., "mode": ..., "max_depth": ..., "max_pages": ...}``.

        Pass ``dlq=DLQ()`` to collect retryable failures in the result.
        Pass ``dlq=DLQ("path/to/dlq.json")`` to also save them to a file.
        Pass ``dlq=result.dlq`` or ``dlq="path/to/dlq.json"`` to retry failures.
        ``url`` and a retry ``dlq`` are mutually exclusive.

        The default behavior is response-only: outputs are returned in memory
        and no markdown/JSON files are written. Use ``output_dest="file"``
        with ``output_dir`` only when you explicitly want SDK convenience file
        output. ``frontmatter=True`` is also an SDK convenience and only
        modifies markdown text returned or saved by this method.

        ``output_format``: ``"markdown"`` (default) or ``"json"``.
        ``output_dest``: ``"response"`` (default) or ``"file"``.

        Example::

            result = rag.scrape("https://example.com/docs")
            result = rag.scrape(["https://example.com/docs", "https://example.com/blog"])
            result = rag.scrape("https://example.com", mode="full", max_depth=2, max_pages=50)

            result = rag.scrape("https://example.com/docs", dlq=DLQ())
            result = rag.scrape("https://example.com/docs", dlq=DLQ("files/dlq/web.json"))
            result = rag.scrape(dlq=result.dlq)
            result = rag.scrape(dlq="files/dlq/web.json")

            rag.scrape("https://example.com/docs", output_dest="file", output_dir="files/output/web")
        """
        is_retry = isinstance(dlq, str) or (isinstance(dlq, DLQ) and bool(dlq.items))

        if is_retry and url is not None:
            raise ValueError("Provide either 'url' or a retry 'dlq', not both")
        if not is_retry and url is None:
            raise ValueError("Provide 'url'")

        if output_format not in {"markdown", "json"}:
            raise ValueError(f"Invalid output_format '{output_format}' — use 'markdown' or 'json'")
        if output_dest not in {"response", "file"}:
            raise ValueError(f"Invalid output_dest '{output_dest}' — use 'response' or 'file'")
        if output_dest == "file" and not output_dir:
            raise ValueError("output_dir is required when output_dest is 'file'")

        if is_retry:
            effective_url, dlq_output_path = self._resolve_dlq_retry(dlq)
        else:
            self._validate_scrape_args(
                url=url,
                mode=mode,
                max_depth=max_depth,
                max_pages=max_pages,
            )
            effective_url = url
            dlq_output_path = dlq.path if isinstance(dlq, DLQ) else None

        try:
            from ragrails.core.stg_01_ingestors.url import scrape_url
            from ragrails.core.stg_01_ingestors.config import UrlIngestorConfig
        except ImportError as exc:
            raise missing_extra("URL ingestion", "url", exc)

        config = UrlIngestorConfig(max_depth=max_depth, max_pages=max_pages)
        stats = run_async(
            scrape_url(
                urls=effective_url,
                mode=mode,
                config=config,
                verbose=verbose,
            )
        )

        outputs = stats.get("outputs", [])
        if frontmatter and output_format == "markdown":
            outputs = with_frontmatter(outputs)
        if output_dest == "file":
            outputs = save_outputs_to_dir(outputs, output_dir, output_format)

        errors = stats.get("errors", [])
        dlq_result = None
        if dlq is not None:
            dlq_items = [
                e["retry_input"]
                for e in errors
                if e.get("isRetryable") and e.get("retry_input")
            ]
            if dlq_output_path and dlq_items:
                self._write_dlq(dlq_items, dlq_output_path)
            dlq_result = DLQ(path=dlq_output_path if dlq_items else None, items=dlq_items)

        return ScrapeResult(
            pages=stats["pages"],
            failed=stats["failed"],
            outputs=outputs,
            errors=errors,
            dlq=dlq_result,
        )

    @staticmethod
    def _resolve_dlq_retry(dlq: DLQ | str) -> tuple[list[dict], str | None]:
        if isinstance(dlq, str):
            try:
                items = json.loads(Path(dlq).read_text(encoding="utf-8"))
            except FileNotFoundError:
                raise ValueError(f"DLQ file not found: '{dlq}'")
            if not isinstance(items, list):
                raise ValueError("DLQ file must contain a JSON array")
            return items, None
        return list(dlq.items), dlq.path

    @staticmethod
    def _write_dlq(items: list[dict], path: str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _validate_scrape_args(
        *,
        url: str | list[str | dict],
        mode: str,
        max_depth: int,
        max_pages: int,
    ) -> None:
        if mode not in {"each", "full"}:
            raise ValueError(f"Invalid mode '{mode}' — use 'each' or 'full'")
        if max_depth < 0:
            raise ValueError("max_depth must be greater than or equal to 0")
        if max_pages < 1:
            raise ValueError("max_pages must be greater than 0")

        urls = [url] if isinstance(url, str) else list(url)
        if not urls:
            raise ValueError("url must include at least one URL")

        for item in urls:
            if isinstance(item, str):
                if not item.strip():
                    raise ValueError("url values must be non-empty strings")
                parsed = urlparse(item)
                if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                    raise ValueError(f"Invalid URL '{item}' — use an absolute http(s) URL")
            elif isinstance(item, dict):
                item_url = item.get("url") or item.get("path")
                if not isinstance(item_url, str) or not item_url.strip():
                    raise ValueError("URL dict entries must include a 'url' key")
            else:
                raise ValueError("url list items must be strings or dicts")


def _setup_error_details(completed: subprocess.CompletedProcess) -> str:
    details = []
    if completed.stderr:
        details.append(f"stderr: {completed.stderr.strip()}")
    if completed.stdout:
        details.append(f"stdout: {completed.stdout.strip()}")
    return "\n" + "\n".join(details) if details else ""
