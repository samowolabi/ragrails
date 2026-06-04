"""REST services for ingestion."""

from __future__ import annotations

from typing import Any

from ragrails.interfaces.sdk import RagRails
from ragrails.interfaces.server.common import model_data, result_data

from .schemas import ApiIngestRequest, DocsIngestRequest, UrlIngestRequest


def _normalize_docs_request(request: DocsIngestRequest) -> dict[str, Any]:
    data = model_data(request)
    files = data.get("files")
    if isinstance(files, list):
        data["files"] = [
            model_data(item) if hasattr(item, "model_dump") or hasattr(item, "dict") else item
            for item in files
        ]
    return data


def fetch_api(request: ApiIngestRequest) -> dict[str, Any]:
    return result_data(RagRails().fetch(**model_data(request)))


def scrape_url(request: UrlIngestRequest) -> dict[str, Any]:
    return result_data(RagRails().scrape(**model_data(request)))


def parse_docs(request: DocsIngestRequest) -> dict[str, Any]:
    return result_data(RagRails().parse(**_normalize_docs_request(request)))
