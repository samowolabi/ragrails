from __future__ import annotations

import json
from pathlib import Path

import click

from ragrails.interfaces.cli.common import exit_with_error, print_errors
from ragrails.interfaces.sdk import RagRails
from ragrails.interfaces.sdk.chat import HistoryCompactionConfig, IntentRoutingConfig, QueryRewriteConfig


@click.command("chat")
@click.argument("query", required=False)
@click.option("--llm-provider", default="openai", show_default=True, help="LLM provider.")
@click.option("--llm-model", default="gpt-4.1-mini", show_default=True, help="LLM model.")
@click.option("--max-tokens", default=1024, show_default=True, help="LLM max output tokens.")
@click.option("--embedder-provider", default="voyage", show_default=True, help="Query embedding provider.")
@click.option("--embedder-model", default="voyage-3", show_default=True, help="Query embedding model.")
@click.option("--vector-db", default="qdrant", show_default=True, type=click.Choice(["qdrant", "pinecone", "weaviate"]), help="Vector database provider.")
@click.option("--collection", default=None, help="Collection, index, or class name.")
@click.option("--url", default=None, help="Vector database URL.")
@click.option("--persona", default="", help="System persona or domain instruction for the chat turn.")
@click.option("--history-file", default=None, help="JSON file containing prior chat history. Updated after the turn.")
@click.option("--rewrite-query", is_flag=True, help="Rewrite follow-up questions before retrieval.")
@click.option("--rewrite-session-context", default="", help="Session context for query rewrite.")
@click.option("--disable-intent-routing", is_flag=True, help="Always run retrieval, including small-talk queries.")
@click.option("--disable-history-compaction", is_flag=True, help="Return full history without SDK compaction.")
@click.option("--rerank", is_flag=True, help="Rerank retrieved chunks before answer generation.")
@click.option("--reranker", default="voyage", show_default=True, help="Reranker provider.")
@click.option("--reranker-model", default="rerank-2-lite", show_default=True, help="Reranker model.")
@click.option("--rerank-top-k", default=5, show_default=True, help="Number of reranked chunks to keep.")
def chat_command(
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
    disable_intent_routing,
    disable_history_compaction,
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

    history = _load_history(history_file)
    rag = RagRails()

    try:
        llm = rag.llm(provider=llm_provider, model=llm_model, max_tokens=max_tokens)
        embedder = rag.embedder(provider=embedder_provider, model=embedder_model, input_type="query")
        reranker_obj = rag.reranker(provider=reranker, model=reranker_model) if rerank else None

        retrieval_config = None
        if rerank:
            from ragrails.core.stg_05_retriever import RetrieverConfig

            retrieval_config = RetrieverConfig(
                use_rerank=True,
                rerank_top_k=rerank_top_k,
            )

        result = rag.chat(
            query,
            llm=llm,
            embedder=embedder,
            vector_db=vector_db,
            collection=collection,
            url=url,
            reranker=reranker_obj,
            history=history,
            history_compaction=HistoryCompactionConfig(enabled=not disable_history_compaction),
            query_rewrite=QueryRewriteConfig(
                enabled=rewrite_query,
                session_context=rewrite_session_context,
            ),
            intent_routing=IntentRoutingConfig(enabled=not disable_intent_routing),
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
