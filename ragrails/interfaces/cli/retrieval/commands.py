"""CLI commands for retrieval."""

from __future__ import annotations

import click

from ragrails.interfaces.cli.config import configured_value
from ragrails.interfaces.cli.common import exit_with_error, print_errors
from ragrails.interfaces.sdk import RagRails


@click.command()
@click.argument("query")
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
def retrieve(ctx, query, vector_db, collection, url, top_k, provider, model, rerank, reranker, reranker_model, rerank_top_k):
    """Retrieve chunks relevant to a query."""
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

    try:
        result = rag.retrieve(
            query,
            top_k=top_k,
            use_rerank=rerank,
            rerank_top_k=rerank_top_k,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Query  : {result.query}")
    click.echo(f"Results: {len(result.items)}")
    for idx, item in enumerate(result.items, start=1):
        score = f"{item.score:.4f}"
        if item.rerank_score is not None:
            score += f" rerank={item.rerank_score:.4f}"
        title = item.metadata.get("title", "")
        path = item.metadata.get("path", "")
        click.echo(f"\n[{idx}] score={score} chunk_id={item.chunk_id} id={item.id}")
        if title:
            click.echo(f"    title: {title}")
        if path:
            click.echo(f"    path : {path}")
        click.echo(f"    text : {item.text[:400]}")
    print_errors(result.errors)


def register(cli: click.Group) -> None:
    cli.add_command(retrieve)
