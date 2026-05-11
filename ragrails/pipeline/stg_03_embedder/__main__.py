"""
Run:
    uv run python -m ragrails.pipeline.stg_03_embedder                                # embed all chunk files
    uv run python -m ragrails.pipeline.stg_03_embedder --input-dir files/output/docs   # embed all chunks in a folder
    uv run python -m ragrails.pipeline.stg_03_embedder file <name>                     # embed a single JSON file
"""

import argparse
import sys

from ragrails.config.settings import Settings
from ragrails.models.embedder.config import EmbedderConfig, create_embedder
from ragrails.models.vector_db.registry import create_vector_store

from .config import EmbedderConfig as PipelineConfig
from .embedder import embed_chunks


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Embed Ragrails chunk JSON files into the configured vector DB.")
    parser.add_argument(
        "mode",
        nargs="?",
        default="all",
        choices=["all", "file"],
        help="Embed all JSON chunk files or one file from the input directory.",
    )
    parser.add_argument(
        "filename",
        nargs="?",
        help="Chunk JSON filename to embed when mode is 'file', e.g. 001_overview.json.",
    )
    parser.add_argument(
        "--input-dir",
        default="files/output/chunks",
        help="Folder containing chunk JSON files. Defaults to files/output/chunks.",
    )
    return parser.parse_args()


settings        = Settings()
embedder_config = EmbedderConfig()
args            = _parse_args()
pipeline_config = PipelineConfig(input_dir=args.input_dir)
embedder        = create_embedder(embedder_config, input_type=pipeline_config.input_type)
vector_store    = create_vector_store(
    provider=settings.vector_db_provider,
    url=settings.vector_db_url,
    collection=settings.collection,
)

if args.mode == "all":
    embed_chunks(model=embedder, store=vector_store, config=pipeline_config)

elif args.mode == "file":
    if not args.filename:
        print("Usage: uv run python -m ragrails.pipeline.stg_03_embedder file <filename.json> [--input-dir files/output/chunks]")
        sys.exit(1)
    embed_chunks(model=embedder, store=vector_store, config=pipeline_config, files=[args.filename])
