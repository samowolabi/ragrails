"""REST schemas for storage."""

from __future__ import annotations

from ragrails.usage.server.embedding.schemas import EmbedRequest as StoreRequest
from ragrails.usage.server.embedding.schemas import EmbedResponse as StoreResponse

__all__ = ["StoreRequest", "StoreResponse"]
