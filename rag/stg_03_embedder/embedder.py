"""
Embedder — encodes chunks with any EmbeddingModel and upserts into any VectorStore.

Processes one file at a time to keep memory flat regardless of corpus size.
The UUID5 id on each chunk ensures upserts are idempotent across re-runs.
"""

import json
from pathlib import Path

from models.embedder.base import EmbeddingModel
from models.vector_db.base import Point, VectorStore
from .config import EmbedderConfig


def _iter_files(chunks_dir: str, files: list[str] | None = None):
    if files:
        return [Path(chunks_dir) / f for f in files]
    return sorted(Path(chunks_dir).glob("*.json"))


def _load_file(path: Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def _build_points(batch: list[dict], vectors: list[list[float]]) -> list[Point]:
    """Map a batch of chunks and their vectors into Point objects for upsert.

    Example:
        _build_points([{"text": "...", "metadata": {"id": "abc", ...}}], [[0.1, 0.2, ...]])
        # → [Point(id="abc", vector=[0.1, 0.2, ...], payload={"text": "...", ...})]
    """
    return [
        Point(
            id=c["metadata"]["id"],
            vector=vec,
            payload={
                "text":          c["text"],
                "source":        c["metadata"].get("source", ""),
                "path":          c["metadata"].get("path", ""),
                "title":         c["metadata"].get("title", ""),
                "description":   c["metadata"].get("description", ""),
                "original_type": c["metadata"].get("original_type", ""),
                "heading":       c["metadata"].get("heading", {}),
                "chunk_id":      c["metadata"].get("chunk_id", ""),
                "chunk_index":   c["metadata"].get("chunk_index", ""),
                "content_hash":  c["metadata"].get("content_hash", ""),
                "table_id":      c["metadata"].get("table_id"),
                "columns":       c["metadata"].get("columns"),
                "row_start":     c["metadata"].get("row_start"),
                "row_end":       c["metadata"].get("row_end"),
            },
        )
        for c, vec in zip(batch, vectors)
    ]


def embed_chunks(
    model: EmbeddingModel,
    store: VectorStore,
    config: EmbedderConfig | None = None,
    files: list[str] | None = None,
) -> None:
    """Embed all chunks in input_dir and upsert into the vector store.

    Streams one file at a time — memory usage stays flat regardless of corpus size.

    Args:
        model:   EmbeddingModel instance (e.g. VoyageModel()).
        store:   VectorStore instance (e.g. QdrantStore(...)).
        config:  EmbedderConfig for input_dir and batch_size.
        files:   Optional list of specific JSON filenames to process.
                 If None, all JSON files in input_dir are processed.

    Example:
        embed_chunks(
            model=VoyageModel(),
            store=QdrantStore(collection="rag_chunks"),
            config=EmbedderConfig(),
        )
        # → embeds all files in files/output/chunks and upserts into Qdrant
    """
    cfg = config or EmbedderConfig()
    paths = list(_iter_files(cfg.input_dir, files))
    if not paths:
        print(f"No chunk files found in {cfg.input_dir}")
        return

    store.ensure_collection(model.vector_size)

    total_upserted = 0

    for file_idx, path in enumerate(paths, start=1):
        chunks = _load_file(path)
        if not chunks:
            continue

        file_upserted = 0
        print(f"\n[{file_idx}/{len(paths)}] {path.name}  ({len(chunks)} chunks)")

        for i in range(0, len(chunks), cfg.batch_size):
            batch = chunks[i: i + cfg.batch_size]
            texts = [c.get("embed_text") or c["text"] for c in batch]
            vectors = model.encode(texts)
            store.upsert(_build_points(batch, vectors))

            file_upserted += len(batch)
            total_upserted += len(batch)
            file_pct    = file_upserted / len(chunks) * 100
            overall_pct = file_idx / len(paths) * 100
            print(f"  chunk {file_upserted}/{len(chunks)} ({file_pct:.0f}%)  |  file {file_idx}/{len(paths)} ({overall_pct:.0f}%)  |  total {total_upserted}")

    print(f"\nDone — {total_upserted} chunks upserted across {len(paths)} files.")
