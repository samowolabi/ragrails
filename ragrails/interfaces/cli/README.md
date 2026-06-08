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
| `doctor` | `doctor` |

## Project Setup

Running `ragrails` with no subcommand starts an interactive setup wizard. Quick
setup writes core defaults to `.ragrails.toml` in the current folder and stores
only non-secret values:

```toml
[vector_store]
provider = "qdrant"
collection = "docs"
url = "http://localhost:6333"

[embedding]
provider = "voyage"
model = "voyage-3"

[llm]
provider = "openai"
model = "gpt-5.5"
max_tokens = 1024

[reranker]
enabled = false
provider = "voyage"
model = "rerank-2-lite"
```

Use `provider = "qdrant_cloud"` with a Qdrant Cloud URL and set
`QDRANT_API_KEY` in your environment.

Advanced setup can also store practical stage defaults:

```toml
[chunking]
chunk_size = 2000
chunk_overlap = 200
min_chunk_length = 100

[embedding]
provider = "voyage"
model = "voyage-3"
batch_size = 64

[storage]
batch_size = 64

[retrieval]
top_k = 10
rerank_top_k = 5

[chat]
query_rewrite = false
intent_routing = true
history_compaction = true
```

Provider API keys stay in environment variables. Commands use this file as
defaults, and command flags override config for one run.

## Doctor

Run `ragrails doctor` to check the local setup before running model-backed
commands. It validates `.ragrails.toml`, supported providers, required values,
provider packages, and environment variables. Use `ragrails doctor --connections`
to also check vector database reachability, and `ragrails doctor --json` for CI.

## Contract

- Keep the CLI file-based where users need shell-friendly stage handoff.
- Keep command modules as thin SDK adapters that translate config and flags into
  `RagRails(...)` setup plus method calls.
- Keep validation and business behavior in the SDK/core layers.
- Add tests beside each CLI module under that module's `tests/` package.
