"""Shared helpers for the Python SDK interface."""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any


def run_async(coro):
    """Run a coroutine, even when called from inside a running event loop."""
    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        return asyncio.run(coro)


def missing_extra(feature: str, extra: str, error: ImportError) -> RuntimeError:
    wrapped = RuntimeError(
        f"{feature} requires optional dependencies. Install them with: "
        f'pip install "ragrails[{extra}]"'
    )
    wrapped.__cause__ = error
    return wrapped


def configured(client: object, name: str) -> dict[str, Any]:
    """Return a copy of a configured SDK default group when available."""
    getter = getattr(client, "_sdk_config", None)
    if callable(getter):
        return getter(name)
    return {}


def configured_object(client: object, name: str, factory):
    """Return a cached configured SDK object when the concrete client supports it."""
    getter = getattr(client, "_sdk_object", None)
    if callable(getter):
        return getter(name, factory)
    return None


def merge_config(defaults: dict[str, Any], overrides: dict[str, Any] | None) -> dict[str, Any]:
    """Merge config dictionaries, dropping unset override values."""
    merged = dict(defaults)
    if overrides:
        merged.update({key: value for key, value in overrides.items() if value is not None})
    return merged


def vector_store_config(
    client: object,
    *,
    vector_db: str | None,
    collection: str | None,
    url: str | None,
    options: dict[str, Any] | None,
) -> tuple[str, str | None, str | None, dict[str, Any] | None]:
    """Resolve constructor vector store defaults and call-level overrides."""
    defaults = configured(client, "vector_store")
    if "provider" in defaults and "vector_db" not in defaults:
        defaults["vector_db"] = defaults.pop("provider")
    if "options" in defaults:
        default_options = defaults.pop("options")
        if default_options is not None and not isinstance(default_options, dict):
            raise TypeError("vector_store.options must be a dictionary")
    else:
        default_options = None
    if options is not None and not isinstance(options, dict):
        raise TypeError("options must be a dictionary")

    merged = merge_config(defaults, {
        "vector_db": vector_db,
        "collection": collection,
        "url": url,
    })
    merged_options = dict(default_options or {})
    if options:
        merged_options.update(options)
    return (
        merged.get("vector_db", "qdrant"),
        merged.get("collection"),
        merged.get("url"),
        merged_options or None,
    )
