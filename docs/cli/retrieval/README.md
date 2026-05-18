# CLI Retrieval

Retrieval searches a configured index for chunks relevant to a query.

## Command

```bash
ragrails retrieve "How do payouts work?" \
  --vector-db qdrant \
  --collection rag_chunks
```

Use reranking:

```bash
ragrails retrieve "How do payouts work?" \
  --vector-db qdrant \
  --collection rag_chunks \
  --top-k 20 \
  --rerank \
  --rerank-top-k 5
```

## Options

| Option | Default | Description |
|---|---|---|
| `QUERY` | - | Search query |
| `--vector-db` | `qdrant` | Vector database provider: `qdrant`, `pinecone`, or `weaviate` |
| `--collection` | - | Source collection or index name |
| `--url` | - | Vector database URL |
| `--top-k` | `10` | Number of chunks to retrieve before reranking |
| `--embedder` | `voyage` | Query embedding provider |
| `--model` | `voyage-3` | Query embedding model |
| `--rerank` | `false` | Rerank retrieved chunks |
| `--reranker` | `voyage` | Reranker provider |
| `--reranker-model` | `rerank-2-lite` | Reranker model |
| `--rerank-top-k` | `5` | Number of chunks to keep after reranking |

Back to the [CLI overview](../README.md).
