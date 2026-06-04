# CLI Storing

Commands for storing and managing embedded chunks in a vector database.

## Commands

| Command | SDK method | Purpose |
|---|---|---|
| `store` | `RagRails().store()` | Upsert embedded chunk dictionaries. |
| `edit` | `RagRails().edit()` | Replace stored chunks by exact chunk ID. |
| `delete` | `RagRails().delete()` | Delete stored chunks by exact chunk ID. |

## Examples

```bash
ragrails store \
  --input-dir files/output/embedded \
  --vector-db qdrant \
  --collection rag_chunks
```

```bash
ragrails edit \
  --input-dir files/output/updates \
  --vector-db qdrant \
  --collection rag_chunks
```

```bash
ragrails delete --id chunk-1 --id chunk-2 --collection rag_chunks
```

Lifecycle commands are chunk-level. Document-level delete and metadata-filter
delete are not part of this interface yet.
