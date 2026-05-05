"""
Async HTTP client with pagination support.

Handles page-based, offset-based, and cursor-based pagination.
Returns raw response data — callers decide how to serialize it.

Pagination config keys:
  type        - "page" | "offset" | "cursor" (omit for single fetch)
  param       - query param name for the page number / offset / cursor value
  size_param  - query param name for page size (optional)
  size        - page size value (optional)
  cursor_path - dot-path into response JSON to find the next cursor value
"""

from typing import Any, AsyncIterator

import httpx


def resolve_path(data: Any, dot_path: str) -> Any:
    """Walk a dot-notation path into nested dicts/lists."""
    obj = data
    for key in dot_path.split("."):
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list) and key.isdigit():
            obj = obj[int(key)]
        else:
            return None
    return obj


def extract_items(data: Any) -> list:
    """Return the list payload from a response — direct list or first list value in a dict."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


async def _fetch(client: httpx.AsyncClient, method: str, url: str, params: dict, body: dict | None) -> Any:
    method = method.upper()
    if method == "GET":
        resp = await client.get(url, params=params)
    elif method == "POST":
        resp = await client.post(url, params=params, json=body)
    elif method == "PUT":
        resp = await client.put(url, params=params, json=body)
    elif method == "PATCH":
        resp = await client.patch(url, params=params, json=body)
    elif method == "DELETE":
        resp = await client.delete(url, params=params)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    resp.raise_for_status()
    return resp.json()


async def fetch_pages(
    url: str,
    method: str = "GET",
    headers: dict | None = None,
    params: dict | None = None,
    body: dict | None = None,
    pagination: dict | None = None,
    max_pages: int = 100,
    timeout: float = 30.0,
) -> AsyncIterator[tuple[int, Any]]:
    """Async generator that yields (page_number, response_data) for each page.

    Args:
        url:        Endpoint URL.
        method:     HTTP method.
        headers:    Request headers (e.g. Authorization).
        params:     Base query parameters.
        body:       Request body for POST/PUT/PATCH.
        pagination: Pagination config dict (see module docstring). None = single fetch.
        max_pages:  Hard cap on number of pages to fetch.
        timeout:    Per-request timeout in seconds.
    """
    pg = pagination or {}
    base_params = dict(params or {})
    if pg.get("size_param") and pg.get("size"):
        base_params[pg["size_param"]] = pg["size"]

    async with httpx.AsyncClient(headers=headers or {}, timeout=timeout) as client:
        page_num = 0
        offset = 0
        cursor = None

        while page_num < max_pages:
            current_params = dict(base_params)
            ptype = pg.get("type")

            if ptype == "page":
                current_params[pg["param"]] = page_num + 1
            elif ptype == "offset":
                current_params[pg["param"]] = offset
            elif ptype == "cursor" and cursor:
                current_params[pg["param"]] = cursor
            elif ptype == "cursor" and page_num > 0:
                break

            data = await _fetch(client, method, url, current_params, body)
            yield page_num + 1, data

            if ptype == "page":
                if not extract_items(data):
                    break
            elif ptype == "offset":
                size = pg.get("size", 100)
                offset += size
                if len(extract_items(data)) < size:
                    break
            elif ptype == "cursor":
                cursor_path = pg.get("cursor_path")
                cursor = resolve_path(data, cursor_path) if cursor_path else None
            else:
                break

            page_num += 1
