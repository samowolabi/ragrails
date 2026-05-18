"""Ragrails CLI entrypoint."""

from __future__ import annotations

import click

from . import chunking, embedding, ingestion, retrieval, storing


@click.group()
@click.version_option(package_name="ragrails")
def cli():
    """Ragrails — ingest, chunk, embed, store, and retrieve RAG content."""


ingestion.register(cli)
chunking.register(cli)
embedding.register(cli)
storing.register(cli)
retrieval.register(cli)
