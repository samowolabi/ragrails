# CLI Chunking

Chunking prints JSON chunks to stdout from markdown text input.

## Commands

| Command | Description |
|---|---|
| `ragrails chunk` | Split markdown text into JSON chunks |

## chunk

```bash
ragrails chunk \
  --markdown "# Guide\n\nUse Ragrails to build a retrieval pipeline."
```

Repeat `--markdown` to chunk multiple documents:

```bash
ragrails chunk \
  --markdown "# Auth\n\nUse a bearer token." \
  --markdown "# Billing\n\nInvoices are generated monthly."
```

Options:

| Option | Default | Description |
|---|---|---|
| `--markdown` | - | Markdown text to chunk. Repeat for multiple documents |
| `--title` | `""` | Title metadata for markdown input |
| `--source` | `""` | Source metadata for markdown input |
| `--chunk-size` | `2000` | Target maximum chunk size |
| `--chunk-overlap` | `200` | Overlap between chunks |
| `--min-chunk-length` | `100` | Minimum chunk length to keep |

Back to the [CLI overview](../README.md).
