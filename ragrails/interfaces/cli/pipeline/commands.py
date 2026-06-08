"""CLI commands for high-level SDK pipelines."""

from __future__ import annotations

import click

from ragrails.interfaces.cli.config import configured_value
from ragrails.interfaces.cli.common import exit_with_error, print_errors
from ragrails.interfaces.sdk import RagRails


@click.command()
@click.option("--markdown", "markdown_items", multiple=True, help="Markdown text to ingest. Repeatable.")
@click.option("--docs", multiple=True, help="Document file to parse and ingest. Repeatable.")
@click.option("--folder", default=None, help="Folder of supported documents to parse and ingest.")
@click.option("--source-url", multiple=True, help="URL to scrape and ingest. Repeatable.")
@click.option("--api-url", default=None, help="API endpoint to fetch and ingest.")
@click.option("--vector-db", default="qdrant", show_default=True, type=click.Choice(["qdrant", "qdrant_cloud", "pinecone", "weaviate"]), help="Vector database provider.")
@click.option("--collection", default=None, help="Collection, index, or class name.")
@click.option("--url", "vector_url", default=None, help="Vector database URL.")
@click.option("--provider", default="voyage", show_default=True, help="Embedding provider.")
@click.option("--model", default="voyage-3", show_default=True, help="Embedding model name.")
@click.option("--batch-size", default=64, show_default=True, help="Chunks per embedding/storage batch.")
@click.option("--chunk-size", default=2000, show_default=True, help="Target maximum chunk size.")
@click.option("--chunk-overlap", default=200, show_default=True, help="Overlap between chunks.")
@click.option("--min-chunk-length", default=100, show_default=True, help="Minimum chunk length to keep.")
@click.option("--concurrency", default="serial", show_default=True, type=click.Choice(["serial", "parallel"]), help="How to run independent source ingestion stages.")
@click.pass_context
def ingest(
    ctx,
    markdown_items,
    docs,
    folder,
    source_url,
    api_url,
    vector_db,
    collection,
    vector_url,
    provider,
    model,
    batch_size,
    chunk_size,
    chunk_overlap,
    min_chunk_length,
    concurrency,
):
    """Run ingestion, chunking, embedding, and storage in one command."""
    vector_db = configured_value(ctx, "vector_db", vector_db, section="vector_store", key="provider", default="qdrant")
    collection = configured_value(ctx, "collection", collection, section="vector_store", key="collection")
    vector_url = configured_value(ctx, "vector_url", vector_url, section="vector_store", key="url")
    provider = configured_value(ctx, "provider", provider, section="embedding", key="provider", default="voyage")
    model = configured_value(ctx, "model", model, section="embedding", key="model", default="voyage-3")
    embed_batch_size = configured_value(ctx, "batch_size", batch_size, section="embedding", key="batch_size", default=64)
    store_batch_size = configured_value(ctx, "batch_size", batch_size, section="storage", key="batch_size", default=64)
    chunk_size = configured_value(ctx, "chunk_size", chunk_size, section="chunking", key="chunk_size", default=2000)
    chunk_overlap = configured_value(ctx, "chunk_overlap", chunk_overlap, section="chunking", key="chunk_overlap", default=200)
    min_chunk_length = configured_value(ctx, "min_chunk_length", min_chunk_length, section="chunking", key="min_chunk_length", default=100)
    if not any([markdown_items, docs, folder, source_url, api_url]):
        raise click.UsageError("Provide at least one source: --markdown, --docs, --folder, --source-url, or --api-url.")
    if docs and folder:
        raise click.UsageError("Use --docs or --folder, not both.")

    docs_input = {"folder": folder} if folder else (list(docs) if docs else None)
    urls_input = list(source_url) if source_url else None

    rag = RagRails(
        collection=collection,
        vector_store={"provider": vector_db, "url": vector_url},
        embedding={"provider": provider, "model": model},
    )

    try:
        result = rag.ingest(
            markdown=list(markdown_items) if markdown_items else None,
            docs=docs_input,
            urls=urls_input,
            api=api_url,
            chunking={
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "min_chunk_length": min_chunk_length,
            },
            embedding={
                "batch_size": embed_batch_size,
            },
            storage={
                "batch_size": store_batch_size,
            },
            concurrency=concurrency,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Sources  : {result.sources}")
    click.echo(f"Chunks   : {result.chunks}")
    click.echo(f"Embedded : {result.embedded}")
    click.echo(f"Stored   : {result.stored}")
    click.echo(f"Failed   : {result.failed}")
    print_errors(result.errors)


@click.command()
@click.argument("query_text")
@click.option("--vector-db", default="qdrant", show_default=True, type=click.Choice(["qdrant", "qdrant_cloud", "pinecone", "weaviate"]), help="Vector database provider.")
@click.option("--collection", default=None, help="Collection, index, or class name.")
@click.option("--url", default=None, help="Vector database URL.")
@click.option("--top-k", default=10, show_default=True, help="Number of results to retrieve.")
@click.option("--provider", default="voyage", show_default=True, help="Query embedding provider.")
@click.option("--model", default="voyage-3", show_default=True, help="Query embedding model.")
@click.option("--rerank/--no-rerank", default=False, help="Rerank retrieved results.")
@click.option("--reranker", default="voyage", show_default=True, help="Reranker provider.")
@click.option("--reranker-model", default="rerank-2-lite", show_default=True, help="Reranker model.")
@click.option("--rerank-top-k", default=5, show_default=True, help="Results to keep after reranking.")
@click.pass_context
def query(ctx, query_text, vector_db, collection, url, top_k, provider, model, rerank, reranker, reranker_model, rerank_top_k):
    """Run query embedding and vector retrieval through the SDK pipeline."""
    vector_db = configured_value(ctx, "vector_db", vector_db, section="vector_store", key="provider", default="qdrant")
    collection = configured_value(ctx, "collection", collection, section="vector_store", key="collection")
    url = configured_value(ctx, "url", url, section="vector_store", key="url")
    provider = configured_value(ctx, "provider", provider, section="embedding", key="provider", default="voyage")
    model = configured_value(ctx, "model", model, section="embedding", key="model", default="voyage-3")
    rerank = configured_value(ctx, "rerank", rerank, section="reranker", key="enabled", default=False)
    reranker = configured_value(ctx, "reranker", reranker, section="reranker", key="provider", default="voyage")
    reranker_model = configured_value(ctx, "reranker_model", reranker_model, section="reranker", key="model", default="rerank-2-lite")
    top_k = configured_value(ctx, "top_k", top_k, section="retrieval", key="top_k", default=10)
    rerank_top_k = configured_value(ctx, "rerank_top_k", rerank_top_k, section="retrieval", key="rerank_top_k", default=5)
    rag = RagRails(
        collection=collection,
        vector_store={"provider": vector_db, "url": url},
        embedding={"provider": provider, "model": model},
        reranker={"enabled": rerank, "provider": reranker, "model": reranker_model},
    )
    rerank_config = {"enabled": False}
    if rerank:
        rerank_config = {
            "enabled": True,
            "top_k": rerank_top_k,
        }

    try:
        result = rag.query(
            query_text,
            retrieval={
                "top_k": top_k,
                "rerank": rerank_config,
            },
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Query  : {result.query}")
    click.echo(f"Results: {len(result.items)}")
    for idx, item in enumerate(result.items, start=1):
        score = f"{item.score:.4f}"
        if item.rerank_score is not None:
            score += f" rerank={item.rerank_score:.4f}"
        click.echo(f"\n[{idx}] score={score} id={item.id}")
        title = item.metadata.get("title", "")
        path = item.metadata.get("path", "")
        if title:
            click.echo(f"    title: {title}")
        if path:
            click.echo(f"    path : {path}")
        click.echo(f"    text : {item.text[:400]}")
    print_errors(result.errors)


def register(cli: click.Group) -> None:
    cli.add_command(ingest)
    cli.add_command(query)
