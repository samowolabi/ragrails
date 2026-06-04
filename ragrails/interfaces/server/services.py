"""Compatibility exports for REST API services."""

from ragrails.interfaces.server.chunking.services import chunk_dir
from ragrails.interfaces.server.chat.services import run_chat
from ragrails.interfaces.server.embedding.services import embed_chunks
from ragrails.interfaces.server.ingestion.services import fetch_api, parse_docs, scrape_url
from ragrails.interfaces.server.pipeline.services import ingest_pipeline, query_pipeline
from ragrails.interfaces.server.retrieval.services import retrieve_chunks
from ragrails.interfaces.server.storing.services import delete_chunks, edit_chunks, store_chunks

__all__ = [
    "chunk_dir",
    "delete_chunks",
    "edit_chunks",
    "embed_chunks",
    "fetch_api",
    "ingest_pipeline",
    "parse_docs",
    "query_pipeline",
    "retrieve_chunks",
    "run_chat",
    "scrape_url",
    "store_chunks",
]
