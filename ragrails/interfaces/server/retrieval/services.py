"""REST services for retrieval."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ragrails import RagRails
from ragrails.interfaces.server.common import model_data

from .schemas import RetrieveRequest


def retrieve_chunks(request: RetrieveRequest) -> dict[str, Any]:
    data = model_data(request)
    query = data.pop("query")
    return asdict(RagRails().retrieve(query, **data))
