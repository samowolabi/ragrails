# CLI Retrieval

Command for searching a stored vector index.

## Command

| Command | SDK methods | Purpose |
|---|---|---|
| `retrieve` | `RagRails().embedder()`, `RagRails().retrieve()` | Embed a query and retrieve relevant chunks. |

## Example

```bash
ragrails retrieve "How do payouts work?" \
  --vector-db qdrant \
  --collection rag_chunks \
  --top-k 10
```

Enable reranking:

```bash
ragrails retrieve "How do payouts work?" \
  --collection rag_chunks \
  --rerank \
  --rerank-top-k 5
```
