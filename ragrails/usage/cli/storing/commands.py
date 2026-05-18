"""CLI commands for storage."""

from __future__ import annotations

import click

from ragrails.usage.cli.common import exit_with_error, print_errors
from ragrails.usage.sdk import RagRails


@click.command()
@click.option("--input-dir", default="files/output/chunks", show_default=True, help="Folder containing chunk JSON files.")
@click.option("--vector-db", default="qdrant", show_default=True, type=click.Choice(["qdrant", "pinecone", "weaviate"]), help="Vector database provider.")
@click.option("--collection", default=None, help="Collection, index, or class name.")
@click.option("--url", default=None, help="Vector database URL.")
@click.option("--files", multiple=True, help="Specific chunk JSON files to store (repeatable).")
@click.option("--batch-size", default=64, show_default=True, help="Chunks per embedding/storage batch.")
@click.option("--embedder", default="voyage", show_default=True, help="Embedding provider.")
@click.option("--model", default="voyage-3", show_default=True, help="Embedding model name.")
def store(input_dir, vector_db, collection, url, files, batch_size, embedder, model):
    """Embed chunk JSON files and store vectors in a vector database."""
    try:
        result = RagRails().store(
            input_dir=input_dir,
            vector_db=vector_db,
            collection=collection,
            url=url,
            files=list(files) if files else None,
            batch_size=batch_size,
            embedder=embedder,
            model=model,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Files stored : {result.files}")
    click.echo(f"Chunks stored: {result.chunks}")
    click.echo(f"Input dir    : {result.input_dir}")
    click.echo(f"Provider     : {result.provider}")
    click.echo(f"Collection   : {result.collection}")
    print_errors(result.errors)


def register(cli: click.Group) -> None:
    cli.add_command(store)
