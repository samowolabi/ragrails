"""Shared helpers for the Python SDK interface."""

from __future__ import annotations

import asyncio
import concurrent.futures


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
