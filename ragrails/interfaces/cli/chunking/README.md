# CLI Chunking

Command for turning ingestion JSON documents into chunk JSON.

## Command

| Command | SDK method | Purpose |
|---|---|---|
| `chunk` | `RagRails().chunk()` | Split ingestion outputs into smaller chunk dictionaries. |

## Example

```bash
ragrails chunk \
  --input-dir files/output/ingestion \
  --output-dir files/output/chunks \
  --chunk-size 1000 \
  --chunk-overlap 100
```

`--input-dir` should contain JSON files with document dictionaries from
`scrape`, `parse`, or `fetch`. The command writes `chunks.json` to
`--output-dir`.
