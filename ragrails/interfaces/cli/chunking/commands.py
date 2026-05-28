"""CLI commands for chunking."""

from __future__ import annotations

import json

import click

from ragrails.interfaces.cli.common import exit_with_error, print_errors
from ragrails.interfaces.sdk import RagRails


@click.command()
@click.option("--markdown", "markdown_items", multiple=True, required=True, help="Markdown text to chunk. Repeat for multiple documents.")
@click.option("--title", default="", help="Title metadata for --markdown content.")
@click.option("--source", default="", help="Source metadata for --markdown content.")
@click.option("--chunk-size", default=2000, show_default=True, help="Target maximum chunk size.")
@click.option("--chunk-overlap", default=200, show_default=True, help="Overlap between chunks.")
@click.option("--min-chunk-length", default=100, show_default=True, help="Minimum chunk length to keep.")
def chunk(markdown_items, title, source, chunk_size, chunk_overlap, min_chunk_length):
    """Split markdown content into chunks and print JSON."""
    try:
        result = RagRails().chunk(
            markdown=list(markdown_items),
            title=title,
            source=source,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(json.dumps(result.items, indent=2))
    print_errors(result.errors)

def register(cli: click.Group) -> None:
    cli.add_command(chunk)
