"""
Doc ingestor — converts local files (PDF, DOCX, CSV, XLSX, etc.) to markdown.

PDF: tries pymupdf4llm first (better layout), falls back to markitdown.
All other formats: markitdown.
"""

import os
import time

import pymupdf4llm
from markitdown import MarkItDown

from utils.frontmatter import build as build_frontmatter, type_from_ext
from ..config import DocsIngestorConfig


def _use_pymupdf4llm(input_file: str) -> str | None:
    try:
        return pymupdf4llm.to_markdown(input_file)
    except Exception as e:
        print(f"  pymupdf4llm failed ({e}), falling back to markitdown")
        return None


def _use_markitdown(input_file: str) -> str | None:
    try:
        return MarkItDown().convert(input_file).text_content
    except Exception as e:
        print(f"  markitdown failed ({e})")
        return None


def _convert(input_file: str) -> str:
    ext = os.path.splitext(input_file)[1].lower()
    if ext == ".pdf":
        return _use_pymupdf4llm(input_file) or _use_markitdown(input_file) or ""
    return _use_markitdown(input_file) or ""


def ingest_doc(
    input_file: str,
    title: str,
    description: str,
    config: DocsIngestorConfig | None = None,
    frontmatter: bool = True,
) -> dict:
    """Convert a single document to markdown and save it with frontmatter."""
    cfg = config or DocsIngestorConfig()
    output_dir = cfg.output_dir
    os.makedirs(output_dir, exist_ok=True)

    start = time.time()
    print(f"[doc] Converting: {input_file}")

    try:
        content = _convert(input_file)
    except Exception as e:
        elapsed = time.time() - start
        message = f"{input_file}: {e}"
        print(f"  → failed ({message}, {elapsed:.2f}s)")
        return {"file": input_file, "output_file": "", "success": False, "size_kb": 0.0, "error": message}

    elapsed = time.time() - start

    if not content:
        print("  → no content extracted")
        return {"file": input_file, "output_file": "", "success": False, "size_kb": 0.0, "error": f"{input_file}: no content extracted"}

    ext = os.path.splitext(input_file)[1]
    metadata = ""
    if frontmatter:
        metadata = build_frontmatter(
            path=os.path.abspath(input_file),
            title=title,
            description=description,
            original_type=type_from_ext(ext),
        )

    basename = os.path.splitext(os.path.basename(input_file))[0]
    output_file = os.path.join(output_dir, f"{basename}.md")
    try:
        with open(output_file, "w") as f:
            f.write(metadata + content)
    except Exception as e:
        message = f"{output_file}: {e}"
        print(f"  → failed writing output ({message})")
        return {"file": input_file, "output_file": "", "success": False, "size_kb": 0.0, "error": message}

    size_kb = len(content.encode()) / 1024
    print(f"  → {output_file}  ({size_kb:.1f} KB, {elapsed:.2f}s)")
    return {"file": input_file, "output_file": output_file, "success": True, "size_kb": size_kb, "error": ""}


def ingest_docs(
    docs: list[dict],
    config: DocsIngestorConfig | None = None,
    frontmatter: bool = True,
) -> dict:
    """Convert multiple documents to markdown.

    Args:
        docs:   List of dicts with keys: filename, title, description.
        config: DocsIngestorConfig for input/output paths.
    """
    if not docs:
        print("No documents specified.")
        return {"documents": 0, "failed": 0, "files": []}

    cfg = config or DocsIngestorConfig()
    print(f"Ingesting {len(docs)} document(s) from {cfg.input_dir}\n")
    results = []
    for doc in docs:
        result = ingest_doc(
            input_file=os.path.join(cfg.input_dir, doc["filename"]),
            title=doc["title"],
            description=doc["description"],
            config=cfg,
            frontmatter=frontmatter,
        )
        results.append(result)

    files = [r["output_file"] for r in results if r["success"]]
    failed = sum(1 for r in results if not r["success"])
    errors = [r["error"] for r in results if not r["success"] and r.get("error")]
    return {"documents": len(files), "failed": failed, "files": files, "errors": errors}
