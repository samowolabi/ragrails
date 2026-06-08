"""Project-local CLI configuration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click


CONFIG_FILENAME = ".ragrails.toml"
VECTOR_DB_CHOICES = ("qdrant", "qdrant_cloud", "pinecone", "weaviate")
LLM_PROVIDER_CHOICES = ("openai", "anthropic", "google")
SECTION_LABELS = {
    "vector_store": "Vector Store",
    "embedding": "Embedding",
    "llm": "LLM",
    "reranker": "Reranker",
    "chunking": "Chunking",
    "storage": "Storage",
    "retrieval": "Retrieval",
    "chat": "Chat",
}


def config_path(cwd: Path | None = None) -> Path:
    return (cwd or Path.cwd()) / CONFIG_FILENAME


def load_config(cwd: Path | None = None) -> dict[str, Any]:
    path = config_path(cwd)
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import tomllib

        return tomllib.loads(text)
    except ModuleNotFoundError:
        return _parse_simple_toml(text)


def save_config(config: dict[str, Any], cwd: Path | None = None) -> Path:
    path = config_path(cwd)
    path.write_text(_format_toml(config), encoding="utf-8")
    return path


def configured_value(
    ctx: click.Context,
    param_name: str,
    value: Any,
    *,
    section: str,
    key: str,
    default: Any = None,
) -> Any:
    """Resolve a command option from CLI flag, config file, then fallback."""
    if _was_passed(ctx, param_name):
        return value
    config_value = load_config().get(section, {}).get(key)
    if config_value not in (None, ""):
        return config_value
    return default


def setup_config() -> None:
    _print_header("Ragrails setup")
    click.echo("Configure project defaults for SDK-backed CLI commands.")
    click.echo()

    current = load_config()
    if current:
        _print_section("Current config")
        click.echo(f"Path: {config_path()}")
        _print_config(current)
        click.echo()
        action = click.prompt(
            "What do you want to do?",
            type=click.Choice(["edit", "reset", "exit"], case_sensitive=False),
            default="edit",
            show_choices=True,
        ).lower()
        if action == "exit":
            click.secho("Config unchanged.", fg="yellow")
            return
        if action == "reset":
            current = {}

    config = _prompt_config(current)
    click.echo()
    if click.confirm("Configure advanced defaults?", default=bool(_has_advanced_config(current))):
        config.update(_prompt_advanced_config(current, config))
    click.echo()
    _print_section("Config preview")
    _print_config(config)
    click.echo()
    path = save_config(config)
    click.secho(f"Saved config to {path}", fg="green")
    _print_env_hints(config)
    _print_next_steps()


def _was_passed(ctx: click.Context, param_name: str) -> bool:
    source = ctx.get_parameter_source(param_name)
    return source is not None and source.name == "COMMANDLINE"


def _prompt_config(current: dict[str, Any]) -> dict[str, Any]:
    vector_store = current.get("vector_store", {})
    embedding = current.get("embedding", {})
    llm = current.get("llm", {})
    reranker = current.get("reranker", {})

    _print_section("Quick setup")
    click.echo()
    _print_section("1. Vector store")
    vector_provider = click.prompt(
        "Vector database provider",
        type=click.Choice(VECTOR_DB_CHOICES, case_sensitive=False),
        default=vector_store.get("provider", "qdrant"),
        show_choices=True,
    ).lower()
    collection = click.prompt("Collection name", default=vector_store.get("collection", "docs"))
    vector_url = click.prompt("Vector database URL", default=vector_store.get("url", ""), show_default=False)

    click.echo()
    _print_section("2. Embedding")
    embedding_provider = click.prompt("Embedding provider", default=embedding.get("provider", "voyage"))
    embedding_model = click.prompt("Embedding model", default=embedding.get("model", "voyage-3"))

    click.echo()
    _print_section("3. LLM")
    llm_provider = click.prompt(
        "LLM provider",
        type=click.Choice(LLM_PROVIDER_CHOICES, case_sensitive=False),
        default=llm.get("provider", "openai"),
        show_choices=True,
    ).lower()
    llm_model = click.prompt("LLM model", default=llm.get("model", "gpt-5.5"))
    max_tokens = click.prompt("LLM max tokens", type=int, default=llm.get("max_tokens", 1024))

    click.echo()
    _print_section("4. Reranking")
    reranker_enabled = click.confirm("Enable reranker?", default=bool(reranker.get("enabled", False)))
    reranker_provider = reranker.get("provider", "voyage")
    reranker_model = reranker.get("model", "rerank-2-lite")
    if reranker_enabled:
        reranker_provider = click.prompt("Reranker provider", default=reranker_provider)
        reranker_model = click.prompt("Reranker model", default=reranker_model)

    return {
        "vector_store": {
            "provider": vector_provider,
            "collection": collection,
            "url": vector_url,
        },
        "embedding": {
            "provider": embedding_provider,
            "model": embedding_model,
        },
        "llm": {
            "provider": llm_provider,
            "model": llm_model,
            "max_tokens": max_tokens,
        },
        "reranker": {
            "enabled": reranker_enabled,
            "provider": reranker_provider,
            "model": reranker_model,
        },
    }


def _prompt_advanced_config(current: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    chunking = current.get("chunking", {})
    embedding = current.get("embedding", {})
    storage = current.get("storage", {})
    retrieval = current.get("retrieval", {})
    chat = current.get("chat", {})

    _print_section("Advanced setup")
    click.echo()
    _print_section("5. Chunking")
    chunk_size = click.prompt("Chunk size", type=int, default=chunking.get("chunk_size", 2000))
    chunk_overlap = click.prompt("Chunk overlap", type=int, default=chunking.get("chunk_overlap", 200))
    min_chunk_length = click.prompt("Minimum chunk length", type=int, default=chunking.get("min_chunk_length", 100))

    click.echo()
    _print_section("6. Batches")
    embedding_batch_size = click.prompt("Embedding batch size", type=int, default=embedding.get("batch_size", 64))
    storage_batch_size = click.prompt("Storage batch size", type=int, default=storage.get("batch_size", 64))

    click.echo()
    _print_section("7. Retrieval")
    top_k = click.prompt("Retrieval top K", type=int, default=retrieval.get("top_k", 10))
    rerank_top_k = click.prompt("Rerank top K", type=int, default=retrieval.get("rerank_top_k", 5))

    click.echo()
    _print_section("8. Chat")
    query_rewrite = click.confirm("Enable query rewrite by default?", default=bool(chat.get("query_rewrite", False)))
    intent_routing = click.confirm("Enable intent routing by default?", default=chat.get("intent_routing", True))
    history_compaction = click.confirm("Enable history compaction by default?", default=chat.get("history_compaction", True))

    embedding_config = dict(config["embedding"])
    embedding_config["batch_size"] = embedding_batch_size
    return {
        "chunking": {
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "min_chunk_length": min_chunk_length,
        },
        "embedding": embedding_config,
        "storage": {
            "batch_size": storage_batch_size,
        },
        "retrieval": {
            "top_k": top_k,
            "rerank_top_k": rerank_top_k,
        },
        "chat": {
            "query_rewrite": query_rewrite,
            "intent_routing": intent_routing,
            "history_compaction": history_compaction,
        },
    }


def _has_advanced_config(config: dict[str, Any]) -> bool:
    return any(config.get(section) for section in ("chunking", "storage", "retrieval", "chat"))


def _print_config(config: dict[str, Any]) -> None:
    for section in ("vector_store", "embedding", "llm", "reranker", "chunking", "storage", "retrieval", "chat"):
        values = config.get(section, {})
        if not values:
            continue
        click.secho(SECTION_LABELS.get(section, section), fg="cyan")
        for key, value in values.items():
            click.echo(f"  {key}: {value}")


def _print_env_hints(config: dict[str, Any]) -> None:
    hints = set()
    embedding_provider = config.get("embedding", {}).get("provider")
    if embedding_provider == "voyage":
        hints.add("VOYAGE_API_KEY")

    reranker_provider = config.get("reranker", {}).get("provider")
    if config.get("reranker", {}).get("enabled") and reranker_provider == "voyage":
        hints.add("VOYAGE_API_KEY")

    llm_provider = config.get("llm", {}).get("provider")
    if llm_provider == "openai":
        hints.add("OPENAI_API_KEY")
    elif llm_provider == "anthropic":
        hints.add("ANTHROPIC_API_KEY")
    elif llm_provider == "google":
        hints.add("GEMINI_API_KEY")

    vector_provider = config.get("vector_store", {}).get("provider")
    if vector_provider == "qdrant_cloud":
        hints.add("QDRANT_API_KEY")
    if vector_provider in {"pinecone", "weaviate"}:
        hints.add("VECTOR_DB_URL")

    if hints:
        click.echo()
        _print_section("Environment")
        click.echo("Set these environment variables before running model-backed commands:")
        for name in sorted(hints):
            click.secho(f"  {name}", fg="yellow")


def _print_header(title: str) -> None:
    line = "=" * max(len(title), 14)
    click.secho(line, fg="cyan")
    click.secho(title, fg="cyan", bold=True)
    click.secho(line, fg="cyan")


def _print_section(title: str) -> None:
    click.secho(title, fg="bright_blue", bold=True)


def _print_next_steps() -> None:
    click.echo()
    _print_section("Next steps")
    click.echo("Run commands without repeating saved defaults:")
    click.echo("  ragrails ingest --docs files/guide.pdf")
    click.echo('  ragrails query "What does the guide cover?"')
    click.echo('  ragrails chat "How do I authenticate?"')


def _format_toml(config: dict[str, Any]) -> str:
    lines: list[str] = []
    for section in ("vector_store", "embedding", "llm", "reranker", "chunking", "storage", "retrieval", "chat"):
        values = config.get(section, {})
        if not values:
            continue
        if lines:
            lines.append("")
        lines.append(f"[{section}]")
        for key, value in values.items():
            lines.append(f"{key} = {_format_value(value)}")
    return "\n".join(lines) + "\n"


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _parse_simple_toml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    current: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = result.setdefault(line[1:-1].strip(), {})
            continue
        if current is None or "=" not in line:
            continue
        key, _, value = line.partition("=")
        current[key.strip()] = _parse_value(value.strip())
    return result


def _parse_value(value: str) -> Any:
    if value in {"true", "false"}:
        return value == "true"
    if value.isdigit():
        return int(value)
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return value
