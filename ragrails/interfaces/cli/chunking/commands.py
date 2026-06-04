"""CLI commands for chunking."""

from __future__ import annotations

import click

from ragrails.interfaces.cli.common import exit_with_error, load_json_dir, print_errors, save_json
from ragrails.interfaces.sdk import RagRails


@click.command()
@click.option("--input-dir", required=True, help="Folder containing ingestion output JSON files.")
@click.option("--output-dir", required=True, help="Folder to write chunk JSON files to.")
@click.option("--chunk-size", default=2000, show_default=True, help="Target maximum chunk size in characters.")
@click.option("--chunk-overlap", default=200, show_default=True, help="Overlap between chunks in characters.")
@click.option("--min-chunk-length", default=100, show_default=True, help="Minimum chunk length to keep.")
def chunk(input_dir, output_dir, chunk_size, chunk_overlap, min_chunk_length):
    """Chunk ingestion output JSON files into smaller pieces."""
    documents = load_json_dir(input_dir)
    if not documents:
        raise click.UsageError(f"No JSON files found in {input_dir}")

    try:
        result = RagRails().chunk(
            markdown=documents,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )
    except Exception as e:
        exit_with_error(e)

    path = save_json(result.items, output_dir, "chunks.json")
    click.echo(f"Documents : {result.inputs}")
    click.echo(f"Chunks    : {result.chunks}")
    click.echo(f"Failed    : {result.failed}")
    click.echo(f"Saved to  : {path}")
    print_errors(result.errors)


def register(cli: click.Group) -> None:
    cli.add_command(chunk)
