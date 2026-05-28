"""Compatibility exports for REST API services."""

from ragrails.interfaces.server.chunking.services import chunk_dir
from ragrails.interfaces.server.embedding.services import embed_chunks
from ragrails.interfaces.server.ingestion.services import fetch_api, parse_docs, scrape_url
from ragrails.interfaces.server.retrieval.services import retrieve_chunks
from ragrails.interfaces.server.storing.services import store_chunks

__all__ = [
    "chunk_dir",
    "embed_chunks",
    "fetch_api",
    "parse_docs",
    "retrieve_chunks",
    "scrape_url",
    "store_chunks",
]
