# REST API Embedding

Embedding creates vectors from chunk JSON files and writes them to the
configured retrieval index.

## Endpoint

```text
POST /v1/embed
```

## Request

```bash
curl -X POST http://127.0.0.1:8000/v1/embed \
  -H "Content-Type: application/json" \
  -d '{
    "input_dir": "files/output/chunks/api",
    "vector_db": "qdrant",
    "collection": "rag_chunks"
  }'
```

Embedding requires the matching vector database extra and provider credentials.

```bash
pip install "ragrails[server,store-qdrant]"
```

Back to the [REST API overview](../README.md).
