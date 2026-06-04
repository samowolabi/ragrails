"""Lifecycle operations for stored vector chunks."""

from __future__ import annotations

from numbers import Real

from ragrails.models.embedder.base import EmbeddingModel
from ragrails.models.vector_db.base import Point, VectorStore


def delete_stored_chunks(*, ids: list[str], store: VectorStore) -> dict:
    """Delete stored chunks by exact chunk IDs."""
    errors = _validate_ids(ids)
    valid_ids = _valid_ids(ids) if isinstance(ids, list) else []
    if not valid_ids:
        return {"deleted": 0, "failed": len(errors), "outputs": [], "errors": errors}

    try:
        store.delete(valid_ids)
    except Exception as e:
        return {
            "deleted": 0,
            "failed": len(valid_ids) + len(errors),
            "outputs": [],
            "errors": errors + [
                _failure(source=",".join(valid_ids), stage="delete", error=str(e), is_retryable=True)
            ],
        }

    return {
        "deleted": len(valid_ids),
        "failed": len(errors),
        "outputs": [{"id": item_id} for item_id in valid_ids],
        "errors": errors,
    }


def edit_stored_chunks(
    *,
    chunks: list[dict],
    embedder: EmbeddingModel,
    store: VectorStore,
    batch_size: int = 64,
) -> dict:
    """Re-embed updated chunks and replace stored vector points by ID."""
    config_error = _validate_batch_size(batch_size)
    if config_error:
        return {"edited": 0, "failed": 1, "outputs": [], "errors": [config_error]}
    if not isinstance(chunks, list):
        return {
            "edited": 0,
            "failed": 1,
            "outputs": [],
            "errors": [_failure(source="", stage="validate", error="chunks must be a list")],
        }

    valid_chunks = []
    errors = []
    for chunk in chunks:
        error = _validate_edit_chunk(chunk)
        if error:
            errors.append(error)
            continue
        valid_chunks.append(chunk)

    if not valid_chunks:
        return {"edited": 0, "failed": len(errors), "outputs": [], "errors": errors}

    try:
        vectors = embedder.encode([chunk["text"] for chunk in valid_chunks])
        if len(vectors) != len(valid_chunks):
            raise ValueError("embedding model returned a different number of vectors than input chunks")
        for vector in vectors:
            _validate_vector(vector)
    except Exception as e:
        return {
            "edited": 0,
            "failed": len(valid_chunks) + len(errors),
            "outputs": [],
            "errors": errors + [
                _failure(source="", stage="embed", error=str(e), is_retryable=True)
            ],
        }

    points = [_to_point(chunk, vector) for chunk, vector in zip(valid_chunks, vectors)]
    outputs = []
    for batch in _batches(points, batch_size):
        try:
            store.upsert(batch)
        except Exception as e:
            for point in batch:
                errors.append(_failure(
                    source=_payload_source(point.payload),
                    stage="upsert",
                    error=str(e),
                    is_retryable=True,
                ))
            continue
        outputs.extend({"id": point.id, "source": _payload_source(point.payload)} for point in batch)

    return {"edited": len(outputs), "failed": len(errors), "outputs": outputs, "errors": errors}


def _validate_ids(ids: list[str]) -> list[dict]:
    if not isinstance(ids, list):
        return [_failure(source="", stage="validate", error="ids must be a list")]
    if not ids:
        return [_failure(source="", stage="validate", error="ids must include at least one chunk ID")]

    errors = []
    for index, item_id in enumerate(ids):
        if not isinstance(item_id, str) or not item_id.strip():
            errors.append(_failure(source="", stage="validate", error=f"ids[{index}] must be a non-empty string"))
    return errors


def _valid_ids(ids: list[str]) -> list[str]:
    return [item_id for item_id in ids if isinstance(item_id, str) and item_id.strip()]


def _validate_batch_size(batch_size: int) -> dict | None:
    if isinstance(batch_size, bool) or not isinstance(batch_size, int):
        return _failure(source="", stage="validate", error="batch_size must be an integer")
    if batch_size < 1:
        return _failure(source="", stage="validate", error="batch_size must be greater than 0")
    return None


def _validate_edit_chunk(chunk: dict) -> dict | None:
    if not isinstance(chunk, dict):
        return _failure(source="", stage="validate", error="chunk must be a dictionary")

    item_id = chunk.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        return _failure(source=_chunk_source(chunk), stage="validate", error="chunk id must be a non-empty string")

    text = chunk.get("text")
    if not isinstance(text, str) or not text.strip():
        return _failure(source=_chunk_source(chunk), stage="validate", error="chunk text must be a non-empty string")

    metadata = chunk.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        return _failure(source=_chunk_source(chunk), stage="validate", error="chunk metadata must be a dictionary")

    return None


def _validate_vector(vector: list[float]) -> None:
    if not isinstance(vector, list) or not vector:
        raise ValueError("embedding must be a non-empty list")
    if any(isinstance(value, bool) or not isinstance(value, Real) for value in vector):
        raise ValueError("embedding values must be numbers")


def _to_point(chunk: dict, vector: list[float]) -> Point:
    metadata = dict(chunk.get("metadata") or {})
    source = chunk.get("source") or metadata.get("source", "")
    payload = dict(metadata)
    payload["text"] = chunk["text"]
    if source:
        payload["source"] = source

    return Point(
        id=chunk["id"],
        vector=[float(value) for value in vector],
        payload=payload,
    )


def _batches(points: list[Point], batch_size: int) -> list[list[Point]]:
    return [points[i: i + batch_size] for i in range(0, len(points), batch_size)]


def _chunk_source(chunk: dict) -> str:
    if isinstance(chunk, dict):
        metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
        return str(chunk.get("source") or metadata.get("source") or chunk.get("id") or metadata.get("id") or "")
    return ""


def _payload_source(payload: dict) -> str:
    return str(payload.get("source") or payload.get("id") or "")


def _failure(
    *,
    source: str,
    stage: str,
    error: str,
    is_retryable: bool = False,
) -> dict:
    return {
        "source": source,
        "source_kind": "stored_chunk",
        "stage": stage,
        "error": error,
        "isRetryable": is_retryable,
        "attempts": 1,
    }
