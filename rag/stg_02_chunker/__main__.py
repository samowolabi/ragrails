"""
Run:
    uv run python -m rag.stg_02_chunker           # chunk all files in default input_dir
    uv run python -m rag.stg_02_chunker dir       # same as above, explicit
    uv run python -m rag.stg_02_chunker file <path>  # chunk a single file and print output
"""

import sys

from .chunker import chunk_dir, chunk_file
from .config import ChunkerConfig

mode = sys.argv[1] if len(sys.argv) > 1 else "dir"

if mode == "dir":
    chunk_dir(config=ChunkerConfig())

elif mode == "file":
    if len(sys.argv) < 3:
        print("Usage: uv run python -m rag.stg_02_chunker file <path>")
        sys.exit(1)
    chunks = chunk_file(sys.argv[2])
    for chunk in chunks:
        print(f"\n[{chunk['metadata']['chunk_id']}] {chunk['metadata'].get('title', '')}")
        print(chunk["text"][:300])

else:
    print(f"Unknown mode '{mode}'. Use: dir | file")
    sys.exit(1)
