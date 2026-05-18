# REST API Storing

`/v1/store` is the storage-oriented endpoint for embedding and storing chunks in
a retrieval index.

## Endpoint

```text
POST /v1/store
```

## Request

```bash
curl -X POST http://127.0.0.1:8000/v1/store \
  -H "Content-Type: application/json" \
  -d '{
    "input_dir": "files/output/chunks/api",
    "vector_db": "qdrant",
    "collection": "rag_chunks"
  }'
```

Back to the [REST API overview](../README.md).
