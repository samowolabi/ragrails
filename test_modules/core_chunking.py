from __future__ import annotations

import json

from ragrails.core.stg_02_chunker.chunker import chunk_markdown_items


def main() -> None:
    result = chunk_markdown_items([
        {
            "text": """
# Core Chunking Test

This script verifies the core chunking module with markdown text input.

## Details

The chunker should return chunk dictionaries with text, embed_text, and metadata
without reading markdown from disk or writing JSON files.
""",
            "source": "manual://core-chunking",
            "title": "Core Chunking Test",
            "metadata": {"source_kind": "manual"},
        }
    ])

    print(json.dumps({
        "chunks": result["chunks"],
        "failed": result["failed"],
        "first": result["outputs"][0] if result["outputs"] else None,
        "errors": result["errors"],
    }, indent=2))


if __name__ == "__main__":
    main()
