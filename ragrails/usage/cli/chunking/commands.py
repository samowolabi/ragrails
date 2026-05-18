"""CLI commands for chunking."""

from __future__ import annotations

import click

from ragrails.usage.cli.common import exit_with_error, print_errors
from ragrails.usage.sdk import RagRails


@click.command()
@click.option("--input-dir", default="files/output/web_crawled", show_default=True, help="Folder containing markdown files.")
@click.option("--output-dir", default="files/output/chunks", show_default=True, help="Folder to write chunk JSON files.")
@click.option("--chunk-size", default=2000, show_default=True, help="Target maximum chunk size.")
@click.option("--chunk-overlap", default=200, show_default=True, help="Overlap between chunks.")
@click.option("--min-chunk-length", default=100, show_default=True, help="Minimum chunk length to keep.")
def chunk(input_dir, output_dir, chunk_size, chunk_overlap, min_chunk_length):
    """Split markdown files into chunk JSON files."""
    try:
        result = RagRails().chunk(
            input_dir=input_dir,
            output_dir=output_dir,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Files chunked : {result.files}")
    click.echo(f"Chunks written: {result.chunks}")
    click.echo(f"Files failed  : {result.failed}")
    click.echo(f"Output dir    : {result.output_dir}")
    for f in result.output_files:
        click.echo(f"  {f}")
    print_errors(result.errors)


@click.command("chunk-file")
@click.argument("path")
@click.option("--chunk-size", default=2000, show_default=True, help="Target maximum chunk size.")
@click.option("--chunk-overlap", default=200, show_default=True, help="Overlap between chunks.")
@click.option("--min-chunk-length", default=100, show_default=True, help="Minimum chunk length to keep.")
def chunk_file(path, chunk_size, chunk_overlap, min_chunk_length):
    """Preview chunks for one markdown file in memory."""
    try:
        chunks = RagRails().chunk_file(
            path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Chunks: {len(chunks)}")
    for idx, item in enumerate(chunks, start=1):
        text = item.get("text", "")
        click.echo(f"\n[{idx}] {text[:300]}")


def register(cli: click.Group) -> None:
    cli.add_command(chunk)
    cli.add_command(chunk_file)
