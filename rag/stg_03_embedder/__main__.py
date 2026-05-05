"""
Run:
    uv run python -m rag.stg_03_embedder              # embed all chunk files
    uv run python -m rag.stg_03_embedder file <name>  # embed a single JSON file, e.g. 001_overview.json
"""

import sys

from config.settings import Settings
from models.embedder.config import EmbedderConfig, create_embedder
from models.vector_db.qdrant import QdrantStore

from .config import EmbedderConfig as PipelineConfig
from .embedder import embed_chunks

settings        = Settings()
embedder_config = EmbedderConfig()
pipeline_config = PipelineConfig()
embedder        = create_embedder(embedder_config, input_type=pipeline_config.input_type)
vector_store    = QdrantStore(url=settings.qdrant_url, collection=settings.collection)

mode = sys.argv[1] if len(sys.argv) > 1 else "all"

if mode == "all":
    embed_chunks(model=embedder, store=vector_store, config=pipeline_config)

elif mode == "file":
    if len(sys.argv) < 3:
        print("Usage: uv run python -m rag.stg_03_embedder file <filename.json>")
        sys.exit(1)
    embed_chunks(model=embedder, store=vector_store, config=pipeline_config, files=[sys.argv[2]])

else:
    print(f"Unknown mode '{mode}'. Use: all | file")
    sys.exit(1)
