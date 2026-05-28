"""Frontmatter utility for SDK ingestion outputs.

Applies YAML frontmatter to markdown outputs at the interface layer.
Only applies when output_format is "markdown" — JSON outputs are unaffected.
"""

from __future__ import annotations


def with_frontmatter(outputs: list[dict]) -> list[dict]:
    """Prepend YAML frontmatter to each output's text field."""
    return [_apply(output) for output in outputs]


def _apply(output: dict) -> dict:
    fm = _build(output)
    if not fm:
        return output
    text = output.get("text", "")
    return {**output, "text": f"{fm}\n\n{text}"}


def _build(output: dict) -> str:
    metadata = output.get("metadata") or {}
    fields: dict[str, str] = {}

    if output.get("title"):
        fields["title"] = str(output["title"])
    if output.get("source"):
        fields["source"] = str(output["source"])
    if output.get("id"):
        fields["id"] = str(output["id"])
    if metadata.get("description"):
        fields["description"] = str(metadata["description"])

    if not fields:
        return ""

    lines = ["---"]
    for key, value in fields.items():
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{key}: "{escaped}"')
    lines.append("---")
    return "\n".join(lines)
