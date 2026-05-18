# CLI Storing

`store` is the storage-oriented CLI command for embedding and storing chunks in
a retrieval index.

## Command

```bash
ragrails store \
  --input-dir files/output/chunks/api \
  --vector-db qdrant \
  --collection rag_chunks
```

## Options

| Option | Default | Description |
|---|---|---|
| `--input-dir` | `files/output/chunks` | Folder containing chunk JSON files |
| `--vector-db` | `qdrant` | Vector database provider: `qdrant`, `pinecone`, or `weaviate` |
| `--collection` | - | Target collection or index name |
| `--url` | - | Vector database URL |
| `--files` | - | Specific chunk JSON files to store. Repeatable |
| `--batch-size` | `64` | Number of chunks to embed and store per batch |
| `--embedder` | `voyage` | Embedding provider |
| `--model` | `voyage-3` | Embedding model name |

Back to the [CLI overview](../README.md).
