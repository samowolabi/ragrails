"""CLI commands for storage."""

from __future__ import annotations

import click

from ragrails.interfaces.cli.common import exit_with_error, load_json_dir, print_errors
from ragrails.interfaces.sdk import RagRails


@click.command()
@click.option("--input-dir", required=True, help="Folder containing embedded chunk JSON files.")
@click.option("--vector-db", default="qdrant", show_default=True, type=click.Choice(["qdrant", "pinecone", "weaviate"]), help="Vector database provider.")
@click.option("--collection", default=None, help="Collection, index, or class name.")
@click.option("--url", default=None, help="Vector database URL.")
@click.option("--batch-size", default=64, show_default=True, help="Chunks per upsert batch.")
def store(input_dir, vector_db, collection, url, batch_size):
    """Store embedded chunk JSON files in a vector database."""
    embedded_chunks = load_json_dir(input_dir)
    if not embedded_chunks:
        raise click.UsageError(f"No JSON files found in {input_dir}")

    try:
        result = RagRails().store(
            embedded_chunks=embedded_chunks,
            vector_db=vector_db,
            collection=collection,
            url=url,
            batch_size=batch_size,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Inputs     : {result.inputs}")
    click.echo(f"Stored     : {result.stored}")
    click.echo(f"Failed     : {result.failed}")
    click.echo(f"Provider   : {result.provider}")
    click.echo(f"Collection : {result.collection}")
    print_errors(result.errors)


@click.command()
@click.option("--input-dir", required=True, help="Folder containing edited chunk JSON files.")
@click.option("--vector-db", default="qdrant", show_default=True, type=click.Choice(["qdrant", "pinecone", "weaviate"]), help="Vector database provider.")
@click.option("--collection", default=None, help="Collection, index, or class name.")
@click.option("--url", default=None, help="Vector database URL.")
@click.option("--provider", default="voyage", show_default=True, help="Embedding provider.")
@click.option("--model", default="voyage-3", show_default=True, help="Embedding model name.")
@click.option("--batch-size", default=64, show_default=True, help="Chunks per edit batch.")
def edit(input_dir, vector_db, collection, url, provider, model, batch_size):
    """Replace stored chunks by exact chunk ID."""
    chunks = load_json_dir(input_dir)
    if not chunks:
        raise click.UsageError(f"No JSON files found in {input_dir}")

    rag = RagRails()
    embedder = rag.embedder(provider=provider, model=model, input_type="document")

    try:
        result = rag.edit(
            chunks=chunks,
            embedder=embedder,
            vector_db=vector_db,
            collection=collection,
            url=url,
            batch_size=batch_size,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Requested  : {result.requested}")
    click.echo(f"Edited     : {result.edited}")
    click.echo(f"Failed     : {result.failed}")
    click.echo(f"Provider   : {result.provider}")
    click.echo(f"Collection : {result.collection}")
    print_errors(result.errors)


@click.command()
@click.option("--id", "ids", multiple=True, required=True, help="Chunk ID to delete. Repeatable.")
@click.option("--vector-db", default="qdrant", show_default=True, type=click.Choice(["qdrant", "pinecone", "weaviate"]), help="Vector database provider.")
@click.option("--collection", default=None, help="Collection, index, or class name.")
@click.option("--url", default=None, help="Vector database URL.")
def delete(ids, vector_db, collection, url):
    """Delete stored chunks by exact chunk ID."""
    try:
        result = RagRails().delete(
            ids=list(ids),
            vector_db=vector_db,
            collection=collection,
            url=url,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Requested  : {result.requested}")
    click.echo(f"Deleted    : {result.deleted}")
    click.echo(f"Failed     : {result.failed}")
    click.echo(f"Provider   : {result.provider}")
    click.echo(f"Collection : {result.collection}")
    print_errors(result.errors)


def register(cli: click.Group) -> None:
    cli.add_command(store)
    cli.add_command(edit)
    cli.add_command(delete)
