"""
Dead letter queue for failed scrape attempts.

Each entry records the URL, error, timestamp, and attempt count.
Failed URLs accumulate across runs — retrying removes them on success.
"""

import json
import os
from datetime import datetime, timezone

from ..config import UrlIngestorConfig

_DEFAULT_PATH = UrlIngestorConfig().dlq_path


def load(path: str = _DEFAULT_PATH) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def save(entries: list[dict], path: str = _DEFAULT_PATH) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)


def push(url: str, error: str, path: str = _DEFAULT_PATH) -> None:
    """Add a failed URL to the DLQ, incrementing attempts if it already exists."""
    entries = load(path)
    for entry in entries:
        if entry["url"] == url:
            entry["attempts"] += 1
            entry["last_error"] = error
            entry["last_failed_at"] = datetime.now(timezone.utc).isoformat()
            save(entries, path)
            return

    entries.append({
        "url":             url,
        "last_error":      error,
        "first_failed_at": datetime.now(timezone.utc).isoformat(),
        "last_failed_at":  datetime.now(timezone.utc).isoformat(),
        "attempts":        1,
    })
    save(entries, path)


def remove(url: str, path: str = _DEFAULT_PATH) -> None:
    """Remove a URL from the DLQ (call on successful retry)."""
    entries = [e for e in load(path) if e["url"] != url]
    save(entries, path)


def pending(path: str = _DEFAULT_PATH, max_attempts: int | None = None) -> list[str]:
    """Return URLs still in the DLQ, optionally capped by attempt count."""
    entries = load(path)
    if max_attempts is not None:
        entries = [e for e in entries if e["attempts"] < max_attempts]
    return [e["url"] for e in entries]


def summary(path: str = _DEFAULT_PATH) -> None:
    entries = load(path)
    if not entries:
        print("DLQ is empty.")
        return
    print(f"DLQ — {len(entries)} failed URL(s):")
    for e in entries:
        print(f"  [{e['attempts']}x] {e['url']}")
        print(f"        {e['last_error']}")
