# Ragrails

[![PyPI](https://img.shields.io/pypi/v/ragrails)](https://pypi.org/project/ragrails/)
[![Python](https://img.shields.io/pypi/pyversions/ragrails)](https://pypi.org/project/ragrails/)
[![Downloads](https://static.pepy.tech/badge/ragrails)](https://pepy.tech/project/ragrails)
[![License](https://img.shields.io/pypi/l/ragrails)](LICENSE)

Ragrails is a modular RAG SDK for turning web pages, local documents, and REST
API responses into retrieval-ready knowledge bases.

Documentation: [https://dev.ragrails.com](https://dev.ragrails.com)

It gives you one Python interface for:

- ingesting URLs, documents, and API responses into markdown
- chunking markdown into RAG-ready JSON chunks
- embedding and storing chunks in pluggable vector databases
- building toward retrieval, chat, and evaluation workflows

```python
from ragrails import RagRails

rag = RagRails()
```

## Install

Ragrails requires **Python 3.10 or newer**. The macOS system Python is 3.9 and
will not work. Install a supported version from [python.org](https://www.python.org/downloads/)
or via your package manager before running the install command.

```bash
pip install ragrails
```

Document and API ingestion are included in the base install. Install extras only
for heavier stages or providers.

| Need | Install |
|---|---|
| URL ingestion | `pip install "ragrails[url]"` |
| Chunking | `pip install "ragrails[chunk]"` |
| REST API server | `pip install "ragrails[server]"` |
| Store in Qdrant | `pip install "ragrails[store-qdrant]"` |
| Store in Pinecone | `pip install "ragrails[store-pinecone]"` |
| Store in Weaviate | `pip install "ragrails[store-weaviate]"` |
| Everything | `pip install "ragrails[all]"` |

Provider extras are also available separately:

| Provider | Install |
|---|---|
| Voyage embeddings | `pip install "ragrails[voyage]"` |
| Qdrant | `pip install "ragrails[qdrant]"` |
| Pinecone | `pip install "ragrails[pinecone]"` |
| Weaviate | `pip install "ragrails[weaviate]"` |
| OpenAI | `pip install "ragrails[openai]"` |
| Anthropic | `pip install "ragrails[anthropic]"` |
| Reranking | `pip install "ragrails[rerank]"` |

## Quick Start

### URL to Vector DB

```bash
pip install "ragrails[url,chunk,voyage,qdrant]"
```

URL scraping uses Playwright through `crawl4ai`. Run browser setup once in the
same environment:

```python
from ragrails import RagRails

rag = RagRails()
rag.setup_url()
```

Then run the pipeline:

```python
from ragrails import RagRails

rag = RagRails()

scraped = rag.scrape(
    url="https://example.com",
    mode="full",
    output_dir="files/output/web_crawled",
)

chunks = rag.chunk(
    input_dir=scraped.output_dir,
    output_dir="files/output/chunks/web",
)

embedded = rag.embed(
    input_dir=chunks.output_dir,
    vector_db="qdrant",
    collection="rag_chunks",
)

print(embedded.chunks)
```

### Documents to Vector DB

```bash
pip install "ragrails[chunk,voyage,qdrant]"
```

```python
from ragrails import RagRails

rag = RagRails()

parsed = rag.parse(
    folder="files/input",
    output_dir="files/output/docs",
)

chunks = rag.chunk(
    input_dir=parsed.output_dir,
    output_dir="files/output/chunks/docs",
)

embedded = rag.embed(
    input_dir=chunks.output_dir,
    vector_db="qdrant",
    collection="rag_chunks",
)

print(embedded.chunks)
```

### API to Markdown

```python
from ragrails import RagRails

result = RagRails().fetch(
    url="https://api.example.com/v1/products",
    title="Products",
    output_dir="files/output/api",
)

print(result.files)
```

## CLI

Ragrails ships with a CLI so you can run the pipeline without writing Python.

```bash
ragrails --help
```

See the [CLI docs](docs/cli/README.md) and stage-specific command docs.

## REST API

Ragrails also ships an optional REST API server for language-agnostic HTTP
usage.

```bash
pip install "ragrails[server]"
ragrails-api
```

See the [REST API docs](docs/server/README.md) and stage-specific endpoint docs.

## SDK Stages

| Stage | Method | Output |
|---|---|---|
| URL ingestion | `rag.scrape(...)` | Markdown files |
| URL retry | `rag.retry_scrape(...)` | Retried markdown files |
| Document ingestion | `rag.parse(...)` | Markdown files |
| API ingestion | `rag.fetch(...)` | Markdown files |
| Chunking | `rag.chunk(...)` | JSON chunk files |
| Single-file chunk preview | `rag.chunk_file(...)` | In-memory chunk dictionaries |
| Embedding | `rag.embed(...)` | Embedded vectors in a vector DB |
| Vector storage | `rag.store(...)` | Alias for embedding and storing chunks |
| Retrieval | `rag.retrieve(...)` | Ranked retrieved chunks |

The usage interfaces are organized in the package under `ragrails/usage/`:

```text
ragrails/usage/
  sdk/
  cli/
  server/
```

Hosted documentation:

- [https://dev.ragrails.com](https://dev.ragrails.com)

Repository docs:

- [Docs index](docs/README.md)

| Usage | Overview | Ingestion | Chunking | Embedding | Storing | Retrieval |
|---|---|---|---|---|---|---|
| SDK | [Overview](docs/sdk/README.md) | [Ingestion](docs/sdk/ingestion/README.md) | [Chunking](docs/sdk/chunking/README.md) | [Embedding](docs/sdk/embedding/README.md) | [Storing](docs/sdk/storing/README.md) | [Retrieval](docs/sdk/retrieval/README.md) |
| CLI | [Overview](docs/cli/README.md) | [Ingestion](docs/cli/ingestion/README.md) | [Chunking](docs/cli/chunking/README.md) | [Embedding](docs/cli/embedding/README.md) | [Storing](docs/cli/storing/README.md) | [Retrieval](docs/cli/retrieval/README.md) |
| REST API server | [Overview](docs/server/README.md) | [Ingestion](docs/server/ingestion/README.md) | [Chunking](docs/server/chunking/README.md) | [Embedding](docs/server/embedding/README.md) | [Storing](docs/server/storing/README.md) | [Retrieval](docs/server/retrieval/README.md) |

Specialized SDK ingestion docs:

- [URL ingestion](docs/sdk/ingestion/url/README.md)
- [Document ingestion](docs/sdk/ingestion/documents/README.md)
- [API ingestion](docs/sdk/ingestion/api/README.md)

Detailed usage, result types, and parameter references live in the stage docs.

## Release Checks

Run all local release checks:

```bash
scripts/test.sh
```

Run individual checks:

```bash
scripts/smoke-test.sh
scripts/test-cli.sh
```

Use the release wrappers so checks run automatically before build or publish:

```bash
scripts/build.sh
scripts/publish.sh
```

## Status

The public SDK currently covers ingestion, chunking, embedding, vector storage,
and retrieval. Chat and eval exist internally and will be exposed as public SDK
surfaces later.
