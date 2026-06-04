# CLI Embedding

Command for embedding chunk JSON and writing embedded chunk JSON.

## Command

| Command | SDK methods | Purpose |
|---|---|---|
| `embed` | `RagRails().embedder()`, `RagRails().embed()` | Create vectors for chunk dictionaries. |

## Example

```bash
ragrails embed \
  --input-dir files/output/chunks \
  --output-dir files/output/embedded \
  --provider voyage \
  --model voyage-3
```

The command writes `embedded.json` to `--output-dir`. Storing is separate so the
embedded output can be inspected or reused before vector database writes.
