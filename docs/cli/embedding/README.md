# CLI Embedding

Embedding creates vectors from chunk JSON files and writes them to the
configured retrieval index.

## Command

```bash
ragrails embed \
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
| `--files` | - | Specific chunk JSON files to embed. Repeatable |
| `--batch-size` | `64` | Number of chunks to embed per batch |
| `--embedder` | `voyage` | Embedding provider |
| `--model` | `voyage-3` | Embedding model name |

Install the matching provider and vector database extras before running this
stage.

Back to the [CLI overview](../README.md).
