"""Storing — writes embedded chunks to a vector store.

Inputs and results stay in memory. File loading belongs in usage layers.
"""

from __future__ import annotations

from numbers import Real

from ragrails.models.vector_db.base import Point, VectorStore

from .config import StoringConfig


def store_embeddings(
    *,
    embedded_chunks: list[dict],
    store: VectorStore,
    config: StoringConfig | None = None,
) -> dict:
    """Store embedded chunk dictionaries in a vector database."""
    cfg = config or StoringConfig()
    config_error = _validate_config(cfg)
    if config_error:
        return {"stored": 0, "failed": 1, "outputs": [], "errors": [config_error]}

    if not isinstance(embedded_chunks, list):
        return {
            "stored": 0,
            "failed": 1,
            "outputs": [],
            "errors": [_failure(source="", stage="validate", error="embedded_chunks must be a list")],
        }

    points = []
    errors = []

    for item in embedded_chunks:
        error = _validate_embedded_chunk(item)
        if error:
            errors.append(error)
            continue
        points.append(_to_point(item))

    points, dimension_errors = _filter_by_vector_size(points)
    errors.extend(dimension_errors)

    if not points:
        return {"stored": 0, "failed": len(errors), "outputs": [], "errors": errors}

    if cfg.ensure_collection:
        try:
            store.ensure_collection(vector_size=len(points[0].vector))
        except Exception as e:
            return {
                "stored": 0,
                "failed": len(points) + len(errors),
                "outputs": [],
                "errors": errors + [
                    _failure(
                        source="",
                        stage="ensure_collection",
                        error=str(e),
                        is_retryable=True,
                    )
                ],
            }

    outputs = []
    for batch in _batches(points, cfg.batch_size):
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

        outputs.extend(_stored_output(point) for point in batch)

    return {"stored": len(outputs), "failed": len(errors), "outputs": outputs, "errors": errors}


def _validate_config(config: StoringConfig) -> dict | None:
    if isinstance(config.batch_size, bool) or not isinstance(config.batch_size, int):
        return _failure(source="", stage="validate", error="batch_size must be an integer")
    if config.batch_size < 1:
        return _failure(source="", stage="validate", error="batch_size must be greater than 0")
    if not isinstance(config.ensure_collection, bool):
        return _failure(source="", stage="validate", error="ensure_collection must be a boolean")
    return None


def _validate_embedded_chunk(item: dict) -> dict | None:
    if not isinstance(item, dict):
        return _failure(source="", stage="validate", error="embedded chunk must be a dictionary")

    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        return _failure(source=_item_source(item), stage="validate", error="embedded chunk id must be a non-empty string")

    text = item.get("text")
    if not isinstance(text, str) or not text.strip():
        return _failure(source=_item_source(item), stage="validate", error="embedded chunk text must be a non-empty string")

    embedding = item.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        return _failure(source=_item_source(item), stage="validate", error="embedding must be a non-empty list")
    if any(isinstance(value, bool) or not isinstance(value, Real) for value in embedding):
        return _failure(source=_item_source(item), stage="validate", error="embedding values must be numbers")

    metadata = item.get("metadata")
    if metadata is not None and not isinstance(metadata, dict):
        return _failure(source=_item_source(item), stage="validate", error="embedded chunk metadata must be a dictionary")

    return None


def _filter_by_vector_size(points: list[Point]) -> tuple[list[Point], list[dict]]:
    if not points:
        return points, []

    vector_size = len(points[0].vector)
    valid_points = []
    errors = []
    for point in points:
        if len(point.vector) != vector_size:
            errors.append(_failure(
                source=_payload_source(point.payload),
                stage="validate",
                error="embedding vector size does not match the first valid embedding",
            ))
            continue
        valid_points.append(point)

    return valid_points, errors


def _to_point(item: dict) -> Point:
    metadata = dict(item.get("metadata") or {})
    source = item.get("source") or metadata.get("source", "")
    payload = dict(metadata)
    payload["text"] = item["text"]
    if source:
        payload["source"] = source

    return Point(
        id=item["id"],
        vector=[float(value) for value in item["embedding"]],
        payload=payload,
    )


def _stored_output(point: Point) -> dict:
    return {
        "id": point.id,
        "source": _payload_source(point.payload),
    }


def _batches(points: list[Point], batch_size: int) -> list[list[Point]]:
    return [points[i: i + batch_size] for i in range(0, len(points), batch_size)]


def _item_source(item: dict) -> str:
    if isinstance(item, dict):
        metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        return str(item.get("source") or metadata.get("source") or item.get("id") or metadata.get("id") or "")
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
        "source_kind": "embedded_chunk",
        "stage": stage,
        "error": error,
        "isRetryable": is_retryable,
        "attempts": 1,
    }
