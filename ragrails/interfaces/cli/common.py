"""Shared CLI helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import NoReturn

import click


def exit_with_error(error: Exception) -> NoReturn:
    click.echo(f"Error: {error}", err=True)
    sys.exit(1)


def parse_pairs(pairs: tuple[str, ...]) -> dict | None:
    result = {}
    for pair in pairs:
        if ":" not in pair:
            raise click.BadParameter(f"Expected KEY:VALUE, got '{pair}'")
        key, _, value = pair.partition(":")
        result[key.strip()] = value.strip()
    return result or None


def print_errors(errors: list) -> None:
    for err in errors:
        msg = err["error"] if isinstance(err, dict) else err
        click.echo(f"Error: {msg}", err=True)


def load_json_dir(input_dir: str) -> list[dict]:
    """Load all JSON files from a directory into a flat list of dicts."""
    items: list[dict] = []
    for path in sorted(Path(input_dir).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            items.extend(data)
        elif isinstance(data, dict):
            items.append(data)
    return items


def save_json(items: list, output_dir: str, filename: str) -> str:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / filename
    path.write_text(json.dumps(items, indent=2), encoding="utf-8")
    return str(path)
