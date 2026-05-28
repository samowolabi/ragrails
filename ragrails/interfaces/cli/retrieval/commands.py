"""CLI commands for retrieval."""

from __future__ import annotations

import click

from ragrails.interfaces.cli.common import exit_with_error
from ragrails.interfaces.sdk import RagRails


@click.command()
@click.argument("query")
@click.option("--vector-db", default="qdrant", show_default=True, type=click.Choice(["qdrant", "pinecone", "weaviate"]), help="Vector database provider.")
@click.option("--collection", default=None, help="Collection, index, or class name.")
@click.option("--url", default=None, help="Vector database URL.")
@click.option("--top-k", default=10, show_default=True, help="Number of vector search candidates.")
@click.option("--embedder", default="voyage", show_default=True, help="Query embedding provider.")
@click.option("--model", default="voyage-3", show_default=True, help="Query embedding model.")
@click.option("--rerank", is_flag=True, help="Rerank retrieved candidates.")
@click.option("--reranker", default="voyage", show_default=True, help="Reranker provider.")
@click.option("--reranker-model", default="rerank-2-lite", show_default=True, help="Reranker model.")
@click.option("--rerank-top-k", default=5, show_default=True, help="Number of reranked results to return.")
def retrieve(query, vector_db, collection, url, top_k, embedder, model, rerank, reranker, reranker_model, rerank_top_k):
    """Retrieve chunks relevant to a query."""
    try:
        result = RagRails().retrieve(
            query,
            vector_db=vector_db,
            collection=collection,
            url=url,
            top_k=top_k,
            embedder=embedder,
            model=model,
            rerank=rerank,
            reranker=reranker,
            reranker_model=reranker_model,
            rerank_top_k=rerank_top_k,
        )
    except Exception as e:
        exit_with_error(e)

    click.echo(f"Query  : {result.query}")
    click.echo(f"Results: {len(result.results)}")
    for idx, item in enumerate(result.results, start=1):
        score = f"{item.score:.4f}"
        if item.rerank_score is not None:
            score += f" rerank={item.rerank_score:.4f}"
        title = item.metadata.get("title", "")
        path = item.metadata.get("path", "")
        click.echo(f"\n[{idx}] score={score} id={item.id}")
        if title:
            click.echo(f"    title: {title}")
        if path:
            click.echo(f"    path : {path}")
        click.echo(f"    text : {item.text[:400]}")


def register(cli: click.Group) -> None:
    cli.add_command(retrieve)
