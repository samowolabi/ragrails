"""API ingestor — fetches paginated REST API responses and returns each page
as a markdown document.
"""

import hashlib
import io
import json
import re
import time
from urllib.parse import urlparse

from markitdown import MarkItDown
from ragrails.tools.api_client import fetch_pages, extract_items
from ..config import ApiIngestorConfig


_md = MarkItDown()


def _json_to_md(data: dict | list, title: str = "") -> str:
    stream = io.BytesIO(json.dumps(data, indent=2).encode())
    content = _md.convert_stream(stream, file_extension=".json").text_content
    return f"# {title}\n\n{content}" if title else content


def _slug(url: str) -> str:
    return re.sub(r"[^\w]", "_", url.split("//")[-1].strip("/"))


def _document_id(source: str, text: str) -> str:
    digest = hashlib.sha256(f"{source}\n{text}".encode("utf-8")).hexdigest()[:16]
    return f"api_{digest}"


def _success(
    *,
    source: str,
    title: str,
    text: str,
    description: str,
    page_num: int,
    item_count: int,
    method: str,
    max_pages: int,
    timeout: float,
    elapsed_seconds: float,
) -> dict:
    return {
        "output": {
            "id": _document_id(source, text),
            "display_id": f"{page_num:03d}_{_slug(source)}",
            "source": source,
            "title": title,
            "text": text,
            "metadata": {
                "source_kind": "api",
                "file_type": "api",
                "description": description,
                "method": method,
                "page": page_num,
                "item_count": item_count,
                "max_pages": max_pages,
                "timeout": timeout,
                "size_bytes": len(text.encode()),
                "elapsed_seconds": elapsed_seconds,
            },
        },
        "error": None,
    }


def _failure(
    *,
    source: str,
    stage: str,
    error: str,
    is_retryable: bool = False,
    attempts: int = 1,
    retry_input: dict | None = None,
) -> dict:
    payload = {
        "source": source,
        "source_kind": "api",
        "stage": stage,
        "error": error,
        "isRetryable": is_retryable,
        "attempts": attempts,
    }
    if retry_input:
        payload["retry_input"] = retry_input
    return {
        "output": None,
        "error": payload,
    }


def _validate_input(url: str, title: str, method: str, max_pages: int, timeout: float) -> None:
    if not isinstance(url, str) or not url.strip():
        raise ValueError("url must be a non-empty string")
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("url must use http:// or https://")
    if not parsed.netloc:
        raise ValueError("url must include a host")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be a non-empty string")
    if method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise ValueError(f"Unsupported HTTP method: {method}")
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or max_pages < 1:
        raise ValueError("max_pages must be a positive integer")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("timeout must be greater than 0")


def _title_from_url(url: str) -> str:
    parsed = urlparse(url)
    tail = parsed.path.rstrip("/").split("/")[-1]
    return tail.replace("-", " ").replace("_", " ").title() or parsed.netloc


def _retry_input(request: dict) -> dict:
    payload = {
        "url": request["url"],
        "title": request["title"],
        "description": request["description"],
        "method": request["method"],
        "max_pages": request["max_pages"],
        "timeout": request["timeout"],
    }
    for key in ("headers", "params", "body", "pagination"):
        if request.get(key) is not None:
            payload[key] = request[key]
    return payload


def _normalize_api_inputs(
    *,
    apis: list[str | dict] | None,
    url: str | None,
    title: str | None,
    description: str,
    method: str,
    headers: dict | None,
    params: dict | None,
    body: dict | None,
    pagination: dict | None,
    max_pages: int,
    timeout: float,
) -> tuple[list[dict], list[dict]]:
    items = apis if apis is not None else [{
        "url": url,
        "title": title,
        "description": description,
        "method": method,
        "headers": headers,
        "params": params,
        "body": body,
        "pagination": pagination,
        "max_pages": max_pages,
        "timeout": timeout,
    }]

    requests = []
    errors = []
    for item in items:
        try:
            request = _normalize_api_input(item, default_max_pages=max_pages, default_timeout=timeout)
            requests.append(request)
        except Exception as e:
            source = item.get("url") if isinstance(item, dict) else str(item)
            errors.append(_failure(source=source or "", stage="validate", error=str(e))["error"])
    return requests, errors


def _normalize_api_input(item: str | dict, *, default_max_pages: int, default_timeout: float) -> dict:
    if isinstance(item, str):
        url = item
        request = {
            "url": url,
            "title": _title_from_url(url),
            "description": "",
            "method": "GET",
            "headers": None,
            "params": None,
            "body": None,
            "pagination": None,
            "max_pages": default_max_pages,
            "timeout": default_timeout,
        }
    elif isinstance(item, dict):
        url = item.get("url")
        request = {
            "url": url,
            "title": item.get("title") or (_title_from_url(url) if isinstance(url, str) and url else ""),
            "description": item.get("description", ""),
            "method": item.get("method", "GET").upper(),
            "headers": item.get("headers"),
            "params": item.get("params"),
            "body": item.get("body"),
            "pagination": item.get("pagination"),
            "max_pages": item.get("max_pages", default_max_pages),
            "timeout": item.get("timeout", default_timeout),
        }
    else:
        raise TypeError("API entries must be strings or dictionaries")

    _validate_input(
        request["url"],
        request["title"],
        request["method"],
        request["max_pages"],
        request["timeout"],
    )
    return request


async def ingest_api(
    url: str | None = None,
    title: str | None = None,
    description: str = "",
    method: str = "GET",
    headers: dict | None = None,
    params: dict | None = None,
    body: dict | None = None,
    pagination: dict | None = None,
    max_pages: int | None = None,
    timeout: float | None = None,
    config: ApiIngestorConfig | None = None,
    apis: list[str | dict] | None = None,
    **_ignored,
) -> dict:
    """Fetch API entries and return markdown documents in memory."""
    cfg = config or ApiIngestorConfig()
    resolved_max_pages = max_pages if max_pages is not None else cfg.max_pages
    resolved_timeout = timeout if timeout is not None else cfg.timeout
    requests, input_errors = _normalize_api_inputs(
        apis=apis,
        url=url,
        title=title,
        description=description,
        method=method,
        headers=headers,
        params=params,
        body=body,
        pagination=pagination,
        max_pages=resolved_max_pages,
        timeout=resolved_timeout,
    )

    results = []
    results.extend({"output": None, "error": error} for error in input_errors)

    for request in requests:
        try:
            async for page_num, data in fetch_pages(
                url=request["url"],
                method=request["method"],
                headers=request["headers"],
                params=request["params"],
                body=request["body"],
                pagination=request["pagination"],
                max_pages=request["max_pages"],
                timeout=request["timeout"],
            ):
                t0 = time.time()
                text = _json_to_md(data, title=f"{request['title']} — page {page_num}")
                elapsed = time.time() - t0
                item_count = len(extract_items(data)) or 1
                results.append(_success(
                    source=request["url"],
                    title=f"{request['title']} — page {page_num}",
                    text=text,
                    description=request["description"],
                    page_num=page_num,
                    item_count=item_count,
                    method=request["method"],
                    max_pages=request["max_pages"],
                    timeout=request["timeout"],
                    elapsed_seconds=elapsed,
                ))

        except Exception as e:
            results.append(_failure(
                source=request["url"],
                stage="request",
                error=str(e),
                is_retryable=True,
                retry_input=_retry_input(request),
            ))

    outputs = [r["output"] for r in results if r.get("output")]
    errors = [r["error"] for r in results if r.get("error")]
    return {"documents": len(outputs), "failed": len(errors), "outputs": outputs, "errors": errors}
