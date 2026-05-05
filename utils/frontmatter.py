"""
Shared frontmatter utilities for all ingestion modules.

Every markdown file produced by the pipeline starts with a metadata block:

    ════════════════════════════════════════
    path:          <url or file path>
    title:         <document title>
    description:   <short description>
    status_code:   <HTTP status or 200>
    crawled_at:    <ISO 8601 timestamp>
    original_type: <web | pdf | csv | docx | xlsx | pptx | txt | html>
    ════════════════════════════════════════

The `════` separator makes the block visually distinct from markdown content.
"""

import re
from datetime import datetime, timezone


SEPARATOR = "═" * 40

_EXT_TYPE = {
    ".pdf":  "pdf",
    ".csv":  "csv",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".pptx": "pptx",
    ".txt":  "txt",
    ".html": "html",
    ".htm":  "html",
    ".md":   "md",
}


def type_from_ext(ext: str) -> str:
    """Map a file extension (with dot) to an original_type string."""
    return _EXT_TYPE.get(ext.lower(), "doc")


def build(
    path: str,
    title: str,
    description: str,
    original_type: str,
    status_code: int | str = 200,
    crawled_at: str | None = None,
    crawl_depth: int | None = None,
) -> str:
    """Return a frontmatter block string to prepend to a markdown file."""
    if crawled_at is None:
        crawled_at = datetime.now(timezone.utc).isoformat()

    def _esc(v: str) -> str:
        return str(v).replace('"', '\\"')

    fields = {
        "path":          path,
        "title":         title,
        "description":   description,
        "status_code":   str(status_code),
        "crawled_at":    crawled_at,
        "original_type": original_type,
    }
    if crawl_depth is not None:
        fields["crawl_depth"] = str(crawl_depth)

    lines = [SEPARATOR]
    for key, val in fields.items():
        if val:
            lines.append(f'{key}: "{_esc(val)}"')
    lines.append(SEPARATOR)
    lines.append("")
    return "\n".join(lines)


def parse(text: str) -> tuple[dict, str]:
    """Extract frontmatter metadata and return (meta dict, remaining body).

    Works with both the new ════ separator and the legacy --- YAML format
    so existing scraped files are not broken.
    """
    # New ════ format
    sep = re.escape(SEPARATOR)
    match = re.match(rf"^{sep}\n(.*?)\n{sep}\n", text, re.DOTALL)
    if match:
        return _parse_fields(match.group(1)), text[match.end():]

    # Legacy --- YAML format
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if match:
        return _parse_fields(match.group(1)), text[match.end():]

    return {}, text


def _parse_fields(block: str) -> dict:
    meta = {}
    for line in block.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip('"')
    # normalise legacy field names
    if "path" not in meta and "url" in meta:
        meta["path"] = meta.pop("url")
    return meta
