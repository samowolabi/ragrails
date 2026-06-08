from __future__ import annotations

import importlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import click

from ragrails.interfaces.cli.config import (
    CONFIG_FILENAME,
    LLM_PROVIDER_CHOICES,
    VECTOR_DB_CHOICES,
    config_path,
    load_config,
)


@dataclass
class Check:
    name: str
    status: str
    message: str
    fix: str = ""


REQUIRED_SECTIONS = ("vector_store", "embedding", "llm", "reranker")
IMPORTS_BY_PROVIDER = {
    "qdrant": ("qdrant_client", 'pip install "ragrails[qdrant]"'),
    "qdrant_cloud": ("qdrant_client", 'pip install "ragrails[qdrant]"'),
    "pinecone": ("pinecone", 'pip install "ragrails[pinecone]"'),
    "weaviate": ("weaviate", 'pip install "ragrails[weaviate]"'),
    "voyage": ("voyageai", 'pip install "ragrails[voyage]"'),
    "openai": ("openai", "pip install ragrails"),
    "anthropic": ("anthropic", "pip install ragrails"),
    "google": ("google.genai", "pip install ragrails"),
}
ENV_BY_PROVIDER = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GEMINI_API_KEY",
    "voyage": "VOYAGE_API_KEY",
    "qdrant_cloud": "QDRANT_API_KEY",
}


@click.command("doctor")
@click.option("--config", "config_file", type=click.Path(path_type=Path), default=None, help="Path to .ragrails.toml.")
@click.option("--connections", is_flag=True, help="Check configured vector database reachability.")
@click.option("--json", "as_json", is_flag=True, help="Print machine-readable JSON output.")
def doctor_command(config_file: Path | None, connections: bool, as_json: bool) -> None:
    """Inspect local Ragrails setup and report missing production prerequisites."""
    checks = run_doctor(config_file=config_file, connections=connections)
    failed = any(check.status == "fail" for check in checks)

    if as_json:
        click.echo(json.dumps({
            "ok": not failed,
            "checks": [asdict(check) for check in checks],
        }, indent=2))
    else:
        _print_report(checks)

    if failed:
        raise click.exceptions.Exit(1)


def run_doctor(config_file: Path | None = None, connections: bool = False) -> list[Check]:
    path = config_file or config_path()
    config = _load_config_from_path(path)
    checks: list[Check] = []

    checks.append(_check_config_file(path, config))
    if not config:
        return checks

    checks.extend(_check_required_sections(config))
    checks.extend(_check_provider_values(config))
    checks.extend(_check_required_values(config))
    checks.extend(_check_imports(config))
    checks.extend(_check_environment(config))
    if connections:
        checks.extend(_check_connections(config))
    else:
        checks.append(Check(
            name="connections",
            status="warn",
            message="Skipped live service checks.",
            fix="Run ragrails doctor --connections to check vector database reachability.",
        ))
    return checks


def _load_config_from_path(path: Path) -> dict[str, Any]:
    if path == config_path(path.parent):
        return load_config(path.parent)
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    try:
        import tomllib

        return tomllib.loads(text)
    except ModuleNotFoundError:
        from ragrails.interfaces.cli.config import _parse_simple_toml

        return _parse_simple_toml(text)


def _check_config_file(path: Path, config: dict[str, Any]) -> Check:
    if not path.exists():
        return Check(
            name="config",
            status="fail",
            message=f"{CONFIG_FILENAME} was not found at {path}.",
            fix="Run ragrails to create project defaults.",
        )
    if not config:
        return Check(
            name="config",
            status="fail",
            message=f"{path} is empty or could not be parsed.",
            fix="Run ragrails and choose reset, or fix the TOML file.",
        )
    return Check(name="config", status="pass", message=f"Loaded {path}.")


def _check_required_sections(config: dict[str, Any]) -> list[Check]:
    checks = []
    for section in REQUIRED_SECTIONS:
        if isinstance(config.get(section), dict) and config[section]:
            checks.append(Check(section, "pass", f"[{section}] is configured."))
        else:
            checks.append(Check(
                section,
                "fail",
                f"[{section}] is missing.",
                "Run ragrails to create or update project defaults.",
            ))
    return checks


def _check_provider_values(config: dict[str, Any]) -> list[Check]:
    checks = []
    vector_provider = config.get("vector_store", {}).get("provider", "")
    checks.append(_choice_check(
        name="vector_store.provider",
        value=vector_provider,
        choices=VECTOR_DB_CHOICES,
    ))

    llm_provider = config.get("llm", {}).get("provider", "")
    checks.append(_choice_check(
        name="llm.provider",
        value=llm_provider,
        choices=LLM_PROVIDER_CHOICES,
    ))
    return checks


def _choice_check(name: str, value: str, choices: tuple[str, ...]) -> Check:
    if value in choices:
        return Check(name=name, status="pass", message=f"{name} is {value}.")
    return Check(
        name=name,
        status="fail",
        message=f"{name} is missing or unsupported: {value or '<empty>'}.",
        fix=f"Use one of: {', '.join(choices)}.",
    )


def _check_required_values(config: dict[str, Any]) -> list[Check]:
    required = [
        ("vector_store.collection", config.get("vector_store", {}).get("collection")),
        ("embedding.provider", config.get("embedding", {}).get("provider")),
        ("embedding.model", config.get("embedding", {}).get("model")),
        ("llm.model", config.get("llm", {}).get("model")),
        ("llm.max_tokens", config.get("llm", {}).get("max_tokens")),
    ]
    checks = []
    for name, value in required:
        if value not in (None, ""):
            checks.append(Check(name=name, status="pass", message=f"{name} is set."))
        else:
            checks.append(Check(name=name, status="fail", message=f"{name} is missing."))
    return checks


def _check_imports(config: dict[str, Any]) -> list[Check]:
    providers = _configured_providers(config)
    checks = []
    for provider in sorted(providers):
        module, install_hint = IMPORTS_BY_PROVIDER.get(provider, ("", ""))
        if not module:
            continue
        if _can_import(module):
            checks.append(Check(name=f"package.{provider}", status="pass", message=f"{module} is importable."))
        else:
            checks.append(Check(
                name=f"package.{provider}",
                status="fail",
                message=f"{module} is not installed.",
                fix=install_hint,
            ))
    return checks


def _check_environment(config: dict[str, Any]) -> list[Check]:
    providers = _configured_providers(config)
    checks = []
    for provider in sorted(providers):
        env_name = ENV_BY_PROVIDER.get(provider)
        if not env_name:
            continue
        if os.environ.get(env_name):
            checks.append(Check(name=f"env.{env_name}", status="pass", message=f"{env_name} is set."))
        else:
            checks.append(Check(
                name=f"env.{env_name}",
                status="fail",
                message=f"{env_name} is not set.",
                fix=f"Export {env_name} before running model-backed commands.",
            ))
    return checks


def _configured_providers(config: dict[str, Any]) -> set[str]:
    providers = {
        config.get("vector_store", {}).get("provider", ""),
        config.get("embedding", {}).get("provider", ""),
        config.get("llm", {}).get("provider", ""),
    }
    reranker = config.get("reranker", {})
    if reranker.get("enabled"):
        providers.add(reranker.get("provider", ""))
    return {provider for provider in providers if provider}


def _check_connections(config: dict[str, Any]) -> list[Check]:
    provider = config.get("vector_store", {}).get("provider", "")
    url = config.get("vector_store", {}).get("url", "")
    if provider in {"qdrant", "qdrant_cloud"}:
        return [_check_qdrant_connection(provider=provider, url=url)]
    if provider in {"pinecone", "weaviate"}:
        return [Check(
            name="connections",
            status="warn",
            message=f"Live connection check is not implemented for {provider} yet.",
            fix="Use the provider dashboard or SDK command to verify connectivity.",
        )]
    return []


def _check_qdrant_connection(provider: str, url: str) -> Check:
    if not url:
        if provider == "qdrant":
            url = "http://localhost:6333"
        else:
            return Check(
                name="connections.qdrant",
                status="fail",
                message="Qdrant Cloud URL is missing.",
                fix="Set vector_store.url in .ragrails.toml.",
            )
    try:
        import httpx

        headers = {}
        api_key = os.environ.get("QDRANT_API_KEY")
        if provider == "qdrant_cloud" and api_key:
            headers["api-key"] = api_key
        response = httpx.get(f"{url.rstrip('/')}/collections", headers=headers, timeout=3.0)
        if 200 <= response.status_code < 300:
            return Check("connections.qdrant", "pass", f"Qdrant responded at {url}.")
        return Check(
            "connections.qdrant",
            "fail",
            f"Qdrant returned HTTP {response.status_code} at {url}.",
            "Check vector_store.url and credentials.",
        )
    except Exception as e:
        return Check(
            "connections.qdrant",
            "fail",
            f"Could not reach Qdrant at {url}: {e}",
            "Start Qdrant, check Docker, or verify the cloud URL.",
        )


def _can_import(module: str) -> bool:
    try:
        importlib.import_module(module)
        return True
    except ImportError:
        return False


def _print_report(checks: list[Check]) -> None:
    click.secho("Ragrails doctor", fg="cyan", bold=True)
    click.echo()
    for check in checks:
        marker = {"pass": "OK", "warn": "WARN", "fail": "FAIL"}[check.status]
        color = {"pass": "green", "warn": "yellow", "fail": "red"}[check.status]
        click.secho(f"{marker:<4} ", fg=color, nl=False, bold=True)
        click.echo(f"{check.name}: {check.message}")
        if check.fix:
            click.echo(f"     Fix: {check.fix}")


def register(cli: click.Group) -> None:
    cli.add_command(doctor_command)


__all__ = ["doctor_command", "register", "run_doctor", "Check"]
