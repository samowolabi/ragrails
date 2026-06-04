# CLI Interface

This package contains the public `ragrails` command-line interface. The CLI is
a thin layer over `ragrails.interfaces.sdk.RagRails`; command modules should
translate terminal inputs into SDK method calls and leave core behavior to the
SDK.

## Modules

| Module | Commands |
|---|---|
| `ingestion` | `setup-url`, `scrape`, `parse`, `fetch` |
| `chunking` | `chunk` |
| `embedding` | `embed` |
| `storing` | `store`, `edit`, `delete` |
| `retrieval` | `retrieve` |
| `pipeline` | `ingest`, `query` |
| `chat` | `chat` |

## Contract

- Keep the CLI file-based where users need shell-friendly stage handoff.
- Keep provider objects inside the CLI; users pass provider/model names.
- Keep validation and business behavior in the SDK/core layers.
- Add tests beside each CLI module under that module's `tests/` package.
