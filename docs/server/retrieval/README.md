# REST API Retrieval

Retrieval searches a configured index for chunks relevant to a query.

## Endpoint

```text
POST /v1/retrieve
```

## Request

```bash
curl -X POST http://127.0.0.1:8000/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do payouts work?",
    "vector_db": "qdrant",
    "collection": "rag_chunks",
    "top_k": 10
  }'
```

Use reranking:

```bash
curl -X POST http://127.0.0.1:8000/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do payouts work?",
    "vector_db": "qdrant",
    "collection": "rag_chunks",
    "top_k": 20,
    "rerank": true,
    "rerank_top_k": 5
  }'
```

Back to the [REST API overview](../README.md).
