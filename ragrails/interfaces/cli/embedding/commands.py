"""CLI commands for embedding."""

from __future__ import annotations

import click

from ragrails.interfaces.cli.common import exit_with_error, load_json_dir, print_errors, save_json
from ragrails.interfaces.sdk import RagRails


@click.command()
@click.option("--input-dir", required=True, help="Folder containing chunk JSON files.")
@click.option("--output-dir", required=True, help="Folder to write embedded chunk JSON files to.")
@click.option("--provider", default="voyage", show_default=True, help="Embedding provider.")
@click.option("--model", default="voyage-3", show_default=True, help="Embedding model name.")
@click.option("--batch-size", default=64, show_default=True, help="Chunks per embedding request.")
def embed(input_dir, output_dir, provider, model, batch_size):
    """Embed chunk JSON files and write vectors to an output directory."""
    chunks = load_json_dir(input_dir)
    if not chunks:
        raise click.UsageError(f"No JSON files found in {input_dir}")

    rag = RagRails()
    embedder = rag.embedder(provider=provider, model=model, input_type="document")

    try:
        result = rag.embed(chunks=chunks, embedder=embedder, batch_size=batch_size)
    except Exception as e:
        exit_with_error(e)

    path = save_json(result.items, output_dir, "embedded.json")
    click.echo(f"Inputs   : {result.inputs}")
    click.echo(f"Embedded : {result.embedded}")
    click.echo(f"Failed   : {result.failed}")
    click.echo(f"Saved to : {path}")
    print_errors(result.errors)


def register(cli: click.Group) -> None:
    cli.add_command(embed)
