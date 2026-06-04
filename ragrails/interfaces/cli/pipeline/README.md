# CLI Pipeline

Convenience commands that call the SDK pipeline helpers.

## Commands

| Command | SDK method | Purpose |
|---|---|---|
| `ingest` | `RagRails().ingest()` | Run ingestion, chunking, embedding, and storage. |
| `query` | `RagRails().query()` | Run query embedding and retrieval. |

## Examples

```bash
ragrails ingest \
  --markdown "# Guide\n\nUse Ragrails for RAG workflows." \
  --vector-db qdrant \
  --collection rag_chunks
```

```bash
ragrails query "What does the guide cover?" \
  --vector-db qdrant \
  --collection rag_chunks
```

Use these commands for quick smoke tests or playground workflows. Use the
stage-specific commands when you need to inspect intermediate files.
