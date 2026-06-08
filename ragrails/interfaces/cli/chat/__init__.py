from __future__ import annotations

import json
from pathlib import Path

import click

from ragrails.interfaces.cli.config import configured_value
from ragrails.interfaces.cli.common import exit_with_error, print_errors
from ragrails.interfaces.sdk import RagRails
from ragrails.interfaces.sdk.chat import HistoryCompactionConfig, IntentRoutingConfig, QueryRewriteConfig


@click.command("chat")
@click.argument("query", required=False)
@click.option("--llm-provider", default="openai", show_default=True, help="LLM provider.")
@click.option("--llm-model", default="gpt-4o-mini", show_default=True, help="LLM model.")
@click.option("--max-tokens", default=1024, show_default=True, help="LLM max output tokens.")
@click.option("--embedder-provider", default="voyage", show_default=True, help="Query embedding provider.")
@click.option("--embedder-model", default="voyage-3", show_default=True, help="Query embedding model.")
@click.option("--vector-db", default="qdrant", show_default=True, type=click.Choice(["qdrant", "qdrant_cloud", "pinecone", "weaviate"]), help="Vector database provider.")
@click.option("--collection", default=None, help="Collection, index, or class name.")
@click.option("--url", default=None, help="Vector database URL.")
@click.option("--persona", default="", help="System persona or domain instruction for the chat turn.")
@click.option("--history-file", default=None, help="JSON file containing prior chat history. Updated after the turn.")
@click.option("--rewrite-query/--no-rewrite-query", default=False, help="Rewrite follow-up questions before retrieval.")
@click.option("--rewrite-session-context", default="", help="Session context for query rewrite.")
@click.option("--intent-routing/--disable-intent-routing", default=True, help="Route small-talk directly to the LLM.")
@click.option("--history-compaction/--disable-history-compaction", default=True, help="Compact long chat history.")
@click.option("--rerank/--no-rerank", default=False, help="Rerank retrieved chunks before answer generation.")
@click.option("--reranker", default="voyage", show_default=True, help="Reranker provider.")
@click.option("--reranker-model", default="rerank-2-lite", show_default=True, help="Reranker model.")
@click.option("--rerank-top-k", default=5, show_default=True, help="Number of reranked chunks to keep.")
@click.pass_context
def chat_command(
    ctx,
    query,
    llm_provider,
    llm_model,
    max_tokens,
    embedder_provider,
    embedder_model,
    vector_db,
    collection,
    url,
    persona,
    history_file,
    rewrite_query,
    rewrite_session_context,
    intent_routing,
    history_compaction,
    rerank,
    reranker,
    reranker_model,
    rerank_top_k,
) -> None:
    """Run one SDK chat turn, or start the interactive chat CLI with no query."""
    if not query:
        from .app import main

        main()
        return

    llm_provider = configured_value(ctx, "llm_provider", llm_provider, section="llm", key="provider", default="openai")
    llm_model = configured_value(ctx, "llm_model", llm_model, section="llm", key="model", default="gpt-4o-mini")
    max_tokens = configured_value(ctx, "max_tokens", max_tokens, section="llm", key="max_tokens", default=1024)
    embedder_provider = configured_value(ctx, "embedder_provider", embedder_provider, section="embedding", key="provider", default="voyage")
    embedder_model = configured_value(ctx, "embedder_model", embedder_model, section="embedding", key="model", default="voyage-3")
    vector_db = configured_value(ctx, "vector_db", vector_db, section="vector_store", key="provider", default="qdrant")
    collection = configured_value(ctx, "collection", collection, section="vector_store", key="collection")
    url = configured_value(ctx, "url", url, section="vector_store", key="url")
    rerank = configured_value(ctx, "rerank", rerank, section="reranker", key="enabled", default=False)
    reranker = configured_value(ctx, "reranker", reranker, section="reranker", key="provider", default="voyage")
    reranker_model = configured_value(ctx, "reranker_model", reranker_model, section="reranker", key="model", default="rerank-2-lite")
    rerank_top_k = configured_value(ctx, "rerank_top_k", rerank_top_k, section="retrieval", key="rerank_top_k", default=5)
    rewrite_query = configured_value(ctx, "rewrite_query", rewrite_query, section="chat", key="query_rewrite", default=False)
    intent_routing = configured_value(ctx, "intent_routing", intent_routing, section="chat", key="intent_routing", default=True)
    history_compaction = configured_value(ctx, "history_compaction", history_compaction, section="chat", key="history_compaction", default=True)
    history = _load_history(history_file)
    rag = RagRails(
        collection=collection,
        vector_store={"provider": vector_db, "url": url},
        embedding={"provider": embedder_provider, "model": embedder_model},
        llm={"provider": llm_provider, "model": llm_model, "max_tokens": max_tokens},
        reranker={"enabled": rerank, "provider": reranker, "model": reranker_model},
    )

    try:
        retrieval_config = None
        if rerank:
            from ragrails.core.stg_05_retriever import RetrieverConfig

            retrieval_config = RetrieverConfig(
                use_rerank=True,
                rerank_top_k=rerank_top_k,
            )

        result = rag.chat(
            query,
            history=history,
            history_compaction=HistoryCompactionConfig(enabled=history_compaction),
            query_rewrite=QueryRewriteConfig(
                enabled=rewrite_query,
                session_context=rewrite_session_context,
            ),
            intent_routing=IntentRoutingConfig(enabled=intent_routing),
            persona=persona,
            retrieval_config=retrieval_config,
        )
    except Exception as e:
        exit_with_error(e)

    if history_file:
        _save_history(history_file, result.history)

    click.echo(result.answer)
    if result.sources:
        click.echo("\nSources:")
        for idx, source in enumerate(result.sources, start=1):
            title = source.get("title") or source.get("path") or source.get("id") or "source"
            click.echo(f"[{idx}] {title}")
    print_errors(result.errors)


def _load_history(path: str | None) -> list[dict]:
    if not path:
        return []
    history_path = Path(path)
    if not history_path.exists():
        return []
    data = json.loads(history_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise click.UsageError("history file must contain a JSON array")
    return data


def _save_history(path: str, history: list[dict]) -> None:
    history_path = Path(path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")


def register(cli: click.Group) -> None:
    cli.add_command(chat_command)


__all__ = ["chat_command", "register"]
