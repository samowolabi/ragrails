"""Shared CLI helpers."""

from __future__ import annotations

import sys
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


def print_errors(errors: list[str]) -> None:
    for err in errors:
        click.echo(f"Error: {err}", err=True)
