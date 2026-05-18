# SDK

The Python SDK is the core Ragrails interface. The CLI and REST API server call
the same SDK methods internally.

## Stages

| Stage | SDK method | Docs |
|---|---|---|
| Ingestion | `scrape`, `parse`, `fetch` | [Ingestion](ingestion/README.md) |
| Chunking | `chunk`, `chunk_file` | [Chunking](chunking/README.md) |
| Embedding | `embed` | [Embedding](embedding/README.md) |
| Storing | `store` | [Storing](storing/README.md) |
| Retrieval | `retrieve` | [Retrieval](retrieval/README.md) |
