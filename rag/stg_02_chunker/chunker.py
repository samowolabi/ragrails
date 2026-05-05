"""
Chunker — splits markdown files into semantically meaningful chunks for RAG.

Strategy:
  1. Split by markdown headers (# / ## / ###) to keep sections together
  2. If a section exceeds the token cap, recursively split by paragraph → sentence
  3. Each chunk carries metadata: source file, url, title, heading path
"""

import json
import hashlib
import os
import re
import uuid

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from .filters import is_nav_chunk, repair_split_links, strip_horizontal_rules, strip_trailing_nav
from .table import segment_tables, chunk_table, parse_headers
from .config import ChunkerConfig
from utils.frontmatter import parse as parse_frontmatter


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


def chunk_file(filepath: str, config: ChunkerConfig | None = None) -> list[dict]:
    """Chunk a single markdown file. Returns a list of chunk dicts.

    Example:
        chunks = chunk_file("files/output/web_crawled/001_overview.md")
        # → [{"text": "...", "embed_text": "...", "metadata": {"title": "...", "chunk_id": "chk_abcd...", ...}}, ...]
    """
    cfg = config or ChunkerConfig()

    with open(filepath) as f:
        raw = f.read()

    raw = re.sub(r"!\[\]\([^)]+\)", "", raw)
    frontmatter, body = parse_frontmatter(raw)

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
            path = frontmatter.get("path", "")
            content_hash = _content_hash(text)
            chunks.append({
                "text": text,
                "metadata": {
                    "source":        filepath,
                    "path":          path,
                    "title":         frontmatter.get("title", "") or os.path.splitext(os.path.basename(filepath))[0],
                    "description":   frontmatter.get("description", ""),
                    "original_type": frontmatter.get("original_type", "")
                                     or ("web" if path.startswith("http") else ""),
                    "heading":       doc.metadata,
                    "chunk_index":   f"{i}_{j}",
                    "chunk_id":      f"chk_{content_hash}",
                    "content_hash":  content_hash,
                    "id":            str(uuid.uuid5(uuid.NAMESPACE_URL, f"{path or filepath}:{content_hash}")),
                },
            })

    chunks = strip_trailing_nav(chunks)
    _annotate_table_chunks(chunks)
    _add_embed_text(chunks)
    return chunks


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
        if not lines or not lines[0].strip().startswith("|"):
            in_table_run = False
            table_id = ""
            continue

        if not in_table_run:
            row_offset = 0
            in_table_run = True

        columns = parse_headers(lines[0])
        if not table_id:
            table_id = _table_id(chunk, columns)
        data_rows = [
            l for l in lines[1:]
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
    source_key = f"{meta.get('path') or meta.get('source')}:{heading_text}:{'|'.join(columns)}"
    digest = hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:16]
    return f"tbl_{digest}"


def chunk_dir(config: ChunkerConfig | None = None) -> None:
    """Chunk all markdown files in input_dir and save as JSON to output_dir.

    Example:
        chunk_dir(ChunkerConfig(input_dir="files/output/web_crawled", output_dir="files/output/chunks"))
        # → writes 001_overview.json, 002_auth.json, ... to files/output/chunks/
    """
    cfg = config or ChunkerConfig()
    os.makedirs(cfg.output_dir, exist_ok=True)

    md_files = [
        os.path.join(cfg.input_dir, f)
        for f in os.listdir(cfg.input_dir)
        if f.endswith(".md")
    ]

    if not md_files:
        print(f"No markdown files found in {cfg.input_dir}")
        return

    print(f"Chunking {len(md_files)} file(s) from {cfg.input_dir}\n")
    total_chunks = 0

    for filepath in md_files:
        chunks = chunk_file(filepath, config=cfg)
        total_chunks += len(chunks)

        basename = os.path.splitext(os.path.basename(filepath))[0]
        out_path = os.path.join(cfg.output_dir, f"{basename}.json")
        with open(out_path, "w") as f:
            json.dump(chunks, f, indent=2)

        print(f"  {os.path.basename(filepath)} → {len(chunks)} chunks → {out_path}")

    print(f"\nTotal: {total_chunks} chunks from {len(md_files)} files")
