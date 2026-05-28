"""Embedder — encodes chunk text with an EmbeddingModel.

Results are returned in memory. Vector-store persistence belongs to storing.
"""

from __future__ import annotations

from ragrails.models.embedder.base import EmbeddingModel

from .config import EmbedderConfig


def embed_chunks(
    *,
    chunks: list[dict],
    model: EmbeddingModel,
    config: EmbedderConfig | None = None,
) -> dict:
    """Embed chunk dictionaries and return embedded chunks in memory."""
    cfg = config or EmbedderConfig()
    config_error = _validate_config(cfg)
    if config_error:
        return {"embedded": 0, "failed": 1, "outputs": [], "errors": [config_error]}

    if not isinstance(chunks, list):
        return {
            "embedded": 0,
            "failed": 1,
            "outputs": [],
            "errors": [_failure(source="", stage="validate", error="chunks must be a list")],
        }

    outputs = []
    errors = []
    valid_chunks = []

    for chunk in chunks:
        error = _validate_chunk(chunk)
        if error:
            errors.append(error)
        else:
            valid_chunks.append(chunk)

    for i in range(0, len(valid_chunks), cfg.batch_size):
        batch = valid_chunks[i: i + cfg.batch_size]
        texts = [_embedding_text(chunk) for chunk in batch]
        try:
            vectors = model.encode(texts)
            if len(vectors) != len(batch):
                raise ValueError("embedding model returned a different number of vectors than input texts")
        except Exception as e:
            for chunk in batch:
                errors.append(_failure(
                    source=_chunk_source(chunk),
                    stage="embed",
                    error=str(e),
                    is_retryable=True,
                ))
            continue

        for chunk, vector in zip(batch, vectors):
            outputs.append(_embedded_chunk(chunk, vector))

    return {"embedded": len(outputs), "failed": len(errors), "outputs": outputs, "errors": errors}


def _validate_config(config: EmbedderConfig) -> dict | None:
    if isinstance(config.batch_size, bool) or not isinstance(config.batch_size, int):
        return _failure(source="", stage="validate", error="batch_size must be an integer")
    if config.batch_size < 1:
        return _failure(source="", stage="validate", error="batch_size must be greater than 0")
    return None


def _validate_chunk(chunk: dict) -> dict | None:
    if not isinstance(chunk, dict):
        return _failure(source="", stage="validate", error="chunk must be a dictionary")
    if not isinstance(chunk.get("text"), str) or not chunk["text"].strip():
        return _failure(source=_chunk_source(chunk), stage="validate", error="chunk text must be a non-empty string")
    metadata = chunk.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        return _failure(source=_chunk_source(chunk), stage="validate", error="chunk metadata must be a dictionary")
    return None


def _embedded_chunk(chunk: dict, vector: list[float]) -> dict:
    metadata = dict(chunk.get("metadata") or {})
    chunk_id = chunk.get("id") or metadata.get("id") or metadata.get("chunk_id")
    embed_text = _embedding_text(chunk)
    return {
        "id": chunk_id,
        "source": chunk.get("source") or metadata.get("source", ""),
        "text": chunk["text"],
        "embed_text": embed_text,
        "embedding": vector,
        "metadata": metadata,
    }


def _embedding_text(chunk: dict) -> str:
    return chunk.get("embed_text") or chunk["text"]


def _chunk_source(chunk: dict) -> str:
    if isinstance(chunk, dict):
        metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
        return str(chunk.get("source") or metadata.get("source") or chunk.get("id") or metadata.get("id") or "")
    return ""


def _failure(
    *,
    source: str,
    stage: str,
    error: str,
    is_retryable: bool = False,
) -> dict:
    return {
        "source": source,
        "source_kind": "chunk",
        "stage": stage,
        "error": error,
        "isRetryable": is_retryable,
        "attempts": 1,
    }
