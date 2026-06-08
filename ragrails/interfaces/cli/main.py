"""Ragrails CLI entrypoint."""

from __future__ import annotations

import click

from . import chat, chunking, doctor, embedding, ingestion, pipeline, retrieval, storing
from .config import setup_config


@click.group(invoke_without_command=True)
@click.version_option(package_name="ragrails")
@click.pass_context
def cli(ctx):
    """Ragrails — ingest, chunk, embed, store, and retrieve RAG content."""
    if ctx.invoked_subcommand is None:
        setup_config()


ingestion.register(cli)
chunking.register(cli)
embedding.register(cli)
storing.register(cli)
retrieval.register(cli)
pipeline.register(cli)
chat.register(cli)
doctor.register(cli)
