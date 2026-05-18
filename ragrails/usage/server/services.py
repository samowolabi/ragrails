"""Compatibility exports for REST API services."""

from ragrails.usage.server.chunking.services import chunk_dir
from ragrails.usage.server.embedding.services import embed_chunks
from ragrails.usage.server.ingestion.services import fetch_api, parse_docs, scrape_url
from ragrails.usage.server.retrieval.services import retrieve_chunks
from ragrails.usage.server.storing.services import store_chunks

__all__ = [
    "chunk_dir",
    "embed_chunks",
    "fetch_api",
    "parse_docs",
    "retrieve_chunks",
    "scrape_url",
    "store_chunks",
]
