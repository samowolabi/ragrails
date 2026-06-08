"""CLI commands for storage."""

from __future__ import annotations

import click

from ragrails.interfaces.cli.config import configured_value
from ragrails.interfaces.cli.common import exit_with_error, load_json_dir, print_errors
from ragrails.interfaces.sdk import RagRails


@click.command()
@click.option("--input-dir", required=True, help="Folder containing embedded chunk JSON files.")
@click.option("--vector-db", default="qdrant", show_default=True, type=click.Choice(["qdrant", "qdrant_cloud", "pinecone", "weaviate"]), help="Vector database provider.")
@click.option("--collection", default=None, help="Collection, index, or class name.")
@click.option("--url", default=None, help="Vector database URL.")
@click.option("--batch-size", default=64, show_default=True, help="Chunks per upsert batch.")
@click.pass_context
def store(ctx, input_dir, vector_db, collection, url, batch_size):
    """Store embedded chunk JSON files in a vector database."""
    vector_db = configured_value(ctx, "vector_db", vector_db, section="vector_store", key="provider", default="qdrant")
    collection = configured_value(ctx, "collection", collection, section="vector_store", key="collection")
    url = configured_value(ctx, "url", url, section="vector_store", key="url")
    batch_size = configured_value(ctx, "batch_size", batch_size, section="storage", key="batch_size", default=64)
    embedded_chunks = load_json_dir(input_dir)
    if not embedded_chunks:
        raise click.UsageError(f"No JSON files found in {input_dir}")

    rag = RagRails(collection=collection, vector_store={"provider": vector_db, "url": url})

    try:
        result = rag.store(
            embedded_chunks=embedded_chunks,
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
@click.option("--vector-db", default="qdrant", show_default=True, type=click.Choice(["qdrant", "qdrant_cloud", "pinecone", "weaviate"]), help="Vector database provider.")
@click.option("--collection", default=None, help="Collection, index, or class name.")
@click.option("--url", default=None, help="Vector database URL.")
@click.option("--provider", default="voyage", show_default=True, help="Embedding provider.")
@click.option("--model", default="voyage-3", show_default=True, help="Embedding model name.")
@click.option("--batch-size", default=64, show_default=True, help="Chunks per edit batch.")
@click.pass_context
def edit(ctx, input_dir, vector_db, collection, url, provider, model, batch_size):
    """Replace stored chunks by exact chunk ID."""
    vector_db = configured_value(ctx, "vector_db", vector_db, section="vector_store", key="provider", default="qdrant")
    collection = configured_value(ctx, "collection", collection, section="vector_store", key="collection")
    url = configured_value(ctx, "url", url, section="vector_store", key="url")
    provider = configured_value(ctx, "provider", provider, section="embedding", key="provider", default="voyage")
    model = configured_value(ctx, "model", model, section="embedding", key="model", default="voyage-3")
    batch_size = configured_value(ctx, "batch_size", batch_size, section="storage", key="batch_size", default=64)
    chunks = load_json_dir(input_dir)
    if not chunks:
        raise click.UsageError(f"No JSON files found in {input_dir}")

    rag = RagRails(
        collection=collection,
        vector_store={"provider": vector_db, "url": url},
        embedding={"provider": provider, "model": model},
    )

    try:
        result = rag.edit(
            chunks=chunks,
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
@click.option("--vector-db", default="qdrant", show_default=True, type=click.Choice(["qdrant", "qdrant_cloud", "pinecone", "weaviate"]), help="Vector database provider.")
@click.option("--collection", default=None, help="Collection, index, or class name.")
@click.option("--url", default=None, help="Vector database URL.")
@click.pass_context
def delete(ctx, ids, vector_db, collection, url):
    """Delete stored chunks by exact chunk ID."""
    vector_db = configured_value(ctx, "vector_db", vector_db, section="vector_store", key="provider", default="qdrant")
    collection = configured_value(ctx, "collection", collection, section="vector_store", key="collection")
    url = configured_value(ctx, "url", url, section="vector_store", key="url")
    rag = RagRails(collection=collection, vector_store={"provider": vector_db, "url": url})

    try:
        result = rag.delete(
            ids=list(ids),
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
