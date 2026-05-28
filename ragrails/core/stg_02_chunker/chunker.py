"""Chunker — splits markdown text into semantically meaningful chunks for RAG.

Strategy:
  1. Split by markdown headers (# / ## / ###) to keep sections together
  2. If a section exceeds the token cap, recursively split by paragraph → sentence
  3. Each chunk carries source, title, description, and heading metadata
"""

import hashlib
import re
import uuid

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from .filters import is_nav_chunk, repair_split_links, strip_horizontal_rules, strip_trailing_nav
from .table import segment_tables, chunk_table, parse_headers
from .config import ChunkerConfig


HEADERS = [
    ("#",   "h1"),
    ("##",  "h2"),
    ("###", "h3"),
]


def _extract_blocks(text: str) -> list[tuple[str, bool]]:
    """Split text into (content, is_atomic) segments.

    Atomic segments (code blocks, tables) are never split internally.

    Example:
        _extract_blocks("Intro.\n```json\n{}\n```\nOutro.")
        # → [("Intro.\n", False), ("```json\n{}\n```", True), ("\nOutro.", False)]
    """
    segments: list[tuple[str, bool]] = []
    for part in re.split(r"(```[\s\S]*?```)", text):
        if part.startswith("```"):
            segments.append((part, True))
        else:
            segments.extend(segment_tables(part))
    return segments


def _code_aware_split(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text at paragraph boundaries, never inside code blocks or tables.

    Example:
        _code_aware_split("Short prose.\n```python\nprint('hello')\n```", chunk_size=2000, chunk_overlap=200)
        # → ["Short prose.\n```python\nprint('hello')\n```"]  (fits in one chunk)
    """
    prose_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    chunks: list[str] = []
    buf = ""

    for part, is_atomic in _extract_blocks(text):
        if not is_atomic and len(part) > chunk_size:
            if buf.strip():
                chunks.append(buf.strip())
                buf = ""
            for sub in prose_splitter.split_text(part):
                if sub.strip():
                    chunks.append(sub.strip())
        elif is_atomic and part.strip().startswith("|") and len(part) > chunk_size:
            if buf.strip():
                chunks.append(buf.strip())
                buf = ""
            for sub in chunk_table(part, chunk_size=chunk_size):
                if sub.strip():
                    chunks.append(sub.strip())
        elif len(buf) + len(part) <= chunk_size:
            buf += part
        else:
            if buf.strip():
                chunks.append(buf.strip())
            if is_atomic:
                lines = buf.strip().splitlines()
                context = next(
                    (l for l in reversed(lines) if l.strip().startswith("#")),
                    next((l for l in reversed(lines) if l.strip()), ""),
                )
                buf = (context + "\n\n" + part).strip() if context else part
            else:
                buf = part

    if buf.strip():
        chunks.append(buf.strip())

    return repair_split_links(chunks)


def chunk_markdown(
    markdown: str,
    *,
    source: str = "",
    metadata: dict | None = None,
    config: ChunkerConfig | None = None,
) -> list[dict]:
    """Chunk markdown content in memory. Returns a list of chunk dicts."""
    if not isinstance(markdown, str):
        raise TypeError("markdown must be a string")

    cfg = config or ChunkerConfig()
    _validate_config(cfg)
    body = re.sub(r"!\[\]\([^)]+\)", "", markdown)
    item_metadata = {k: v for k, v in (metadata or {}).items() if v is not None}

    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS,
        strip_headers=False,
    )
    header_chunks = header_splitter.split_text(body)

    chunks = []
    for i, doc in enumerate(header_chunks):
        sub_chunks = _code_aware_split(doc.page_content, cfg.chunk_size, cfg.chunk_overlap)
        for j, text in enumerate(sub_chunks):
            text = strip_horizontal_rules(text)
            if not text.strip() or len(text.strip()) < cfg.min_chunk_length:
                continue
            if is_nav_chunk(text):
                continue
            title = item_metadata.get("title", "")
            description = item_metadata.get("description", "")
            source_kind = item_metadata.get("source_kind", "markdown")
            original_type = item_metadata.get("original_type", source_kind)
            content_hash = _content_hash(text)
            chunks.append({
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source}:{content_hash}")),
                "source": source,
                "text": text,
                "metadata": {
                    "source": source,
                    "source_kind": source_kind,
                    "title": title,
                    "description": description,
                    "original_type": original_type,
                    "heading": doc.metadata,
                    "chunk_index": f"{i}_{j}",
                    "chunk_id": f"chk_{content_hash}",
                    "content_hash": content_hash,
                    "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source}:{content_hash}")),
                },
            })

    chunks = strip_trailing_nav(chunks)
    _annotate_table_chunks(chunks)
    _add_embed_text(chunks)
    return chunks


def chunk_markdown_items(
    items: list[str | dict],
    *,
    config: ChunkerConfig | None = None,
) -> dict:
    """Chunk multiple markdown text entries and return a structured result."""
    if not isinstance(items, list):
        return {
            "chunks": 0,
            "failed": 1,
            "outputs": [],
            "errors": [_failure(
                source="",
                error="items must be a list",
                stage="validate",
            )],
        }
    if not items:
        return {"chunks": 0, "failed": 0, "outputs": [], "errors": []}

    results = []
    for item in items:
        try:
            normalized = _normalize_markdown_item(item)
            chunks = chunk_markdown(
                normalized["text"],
                source=normalized["source"],
                metadata=normalized["metadata"],
                config=config,
            )
            results.append({"outputs": chunks, "error": None})
        except Exception as e:
            results.append({
                "outputs": [],
                "error": _failure(
                    source=_item_error_source(item),
                    error=str(e),
                    stage="validate",
                ),
            })

    outputs = [chunk for result in results for chunk in result["outputs"]]
    errors = [result["error"] for result in results if result["error"]]
    return {"chunks": len(outputs), "failed": len(errors), "outputs": outputs, "errors": errors}


def _normalize_markdown_item(item: str | dict) -> dict:
    if isinstance(item, str):
        return {"text": item, "source": "", "metadata": {}}
    if not isinstance(item, dict):
        raise TypeError("chunk items must be strings or dictionaries")

    text = item.get("text") or item.get("markdown")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("chunk item text must be a non-empty string")

    metadata = dict(item.get("metadata") or {})
    for key in ("title", "description", "source_kind", "original_type"):
        if key in item and item[key] is not None:
            metadata[key] = item[key]

    return {
        "text": text,
        "source": item.get("source", ""),
        "metadata": metadata,
    }


def _validate_config(config: ChunkerConfig) -> None:
    for field in ("chunk_size", "chunk_overlap", "min_chunk_length"):
        value = getattr(config, field)
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{field} must be an integer")
    if config.chunk_size < 1:
        raise ValueError("chunk_size must be greater than 0")
    if config.chunk_overlap < 0:
        raise ValueError("chunk_overlap must be greater than or equal to 0")
    if config.chunk_overlap >= config.chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    if config.min_chunk_length < 1:
        raise ValueError("min_chunk_length must be greater than 0")


def _failure(*, source: str, error: str, stage: str) -> dict:
    return {
        "source": source,
        "source_kind": "markdown",
        "stage": stage,
        "error": error,
        "isRetryable": False,
        "attempts": 1,
    }


def _item_error_source(item: str | dict) -> str:
    if isinstance(item, dict):
        return str(item.get("source") or item.get("path") or item.get("title") or item)
    return ""


def _content_hash(text: str) -> str:
    """Return a compact hash for stable chunk identity across position changes."""
    normalized = " ".join(text.split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _add_embed_text(chunks: list[dict]) -> None:
    """Add embed_text field — title + heading + description + text — for the embedding model.

    Example:
        chunk = {"text": "Use Bearer token.", "metadata": {"title": "Auth", "heading": {"h2": "Overview"}}}
        _add_embed_text([chunk])
        # → chunk["embed_text"] == "Auth\nOverview\n\nUse Bearer token."
    """
    for chunk in chunks:
        meta = chunk["metadata"]
        parts = []

        if meta.get("title"):
            parts.append(meta["title"])

        heading = meta.get("heading", {})
        if heading:
            parts.append(" > ".join(heading.values()))

        if meta.get("description"):
            parts.append(meta["description"])

        embed_text = ("\n".join(parts) + "\n\n" + chunk["text"]) if parts else chunk["text"]
        chunk["embed_text"] = embed_text


def _annotate_table_chunks(chunks: list[dict]) -> None:
    """Add table metadata to table chunks in-place.

    Example:
        chunk = {"text": "| Name | Code |\n|------|------|\n| GTBank | 058 |", "metadata": {}}
        _annotate_table_chunks([chunk])
        # → chunk["metadata"] includes columns, table_id, row_start, row_end
    """
    row_offset = 0
    in_table_run = False
    table_id = ""

    for chunk in chunks:
        lines = [l for l in chunk["text"].splitlines() if l.strip()]
        table_start = next((i for i, line in enumerate(lines) if line.strip().startswith("|")), None)
        if table_start is None:
            in_table_run = False
            table_id = ""
            continue
        table_lines = lines[table_start:]

        if not in_table_run:
            row_offset = 0
            in_table_run = True

        columns = parse_headers(table_lines[0])
        if not table_id:
            table_id = _table_id(chunk, columns)
        data_rows = [
            l for l in table_lines[1:]
            if not re.match(r"^\|[-| :]+\|$", l.strip())
        ]
        chunk["metadata"]["columns"]   = columns
        chunk["metadata"]["table_id"]  = table_id
        chunk["metadata"]["row_start"] = row_offset + 1
        chunk["metadata"]["row_end"]   = row_offset + len(data_rows)
        row_offset += len(data_rows)


def _table_id(chunk: dict, columns: list[str]) -> str:
    """Return a stable id for chunks from the same split table run."""
    meta = chunk["metadata"]
    heading = meta.get("heading", {})
    heading_text = " > ".join(heading.values()) if isinstance(heading, dict) else str(heading or "")
    source_key = f"{meta.get('source')}:{heading_text}:{'|'.join(columns)}"
    digest = hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:16]
    return f"tbl_{digest}"
