# CLI

The Ragrails CLI lets you run each RAG pipeline stage from the terminal without
writing Python.

## Install

```bash
pip install ragrails
```

Verify:

```bash
ragrails --help
```

## Stage Docs

| Stage | Commands | Docs |
|---|---|---|
| Ingestion | `setup-url`, `scrape`, `parse`, `fetch` | [Ingestion](ingestion/README.md) |
| Chunking | `chunk` | [Chunking](chunking/README.md) |
| Embedding | `embed` | [Embedding](embedding/README.md) |
| Storing | `store` | [Storing](storing/README.md) |
| Retrieval | `retrieve` | [Retrieval](retrieval/README.md) |

Back to the [docs index](../README.md).
