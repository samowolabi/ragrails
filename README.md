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

Chunking, the CLI, REST API server, document ingestion, and API
ingestion are included in the base install. Install extras only for URL
scraping and provider integrations.

Extras are optional because they install provider SDKs, browser/crawler
dependencies, or heavier runtime packages that not every project needs.

| Need | Install |
|---|---|
| URL ingestion | `pip install "ragrails[url]"` |
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
)

chunks = rag.chunk(
    markdown=[
        {"markdown": "# Example\n\nScraped markdown content", "source": "https://example.com"}
    ],
)

print(chunks.items)
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
)

chunks = rag.chunk(
    markdown=[
        {"markdown": "# Guide\n\nParsed markdown content", "source": "guide.pdf"}
    ],
)

print(chunks.items)
```

### API to Markdown

```python
from ragrails import RagRails

result = RagRails().fetch(
    url="https://api.example.com/v1/products",
    title="Products",
)

print(result.outputs[0]["text"])
```

## CLI

Ragrails ships with a CLI so you can run the pipeline without writing Python.

```bash
ragrails --help
```

See the [CLI docs](docs/cli/README.md) and stage-specific command docs.

## REST API

Ragrails also ships a REST API server for language-agnostic HTTP usage.

```bash
ragrails-api
```

See the [REST API docs](docs/server/README.md) and stage-specific endpoint docs.
Swagger UI is available at `http://127.0.0.1:8000/docs` when the server is
running. The OpenAPI schema is available at `/v1/openapi.json`.

## Notebooks

The repository includes Jupyter notebooks for interactive SDK workflows:

| Notebook | Stage |
|---|---|
| `notebooks/01_ingestion.ipynb` | Ingestion |
| `notebooks/02_chunking.ipynb` | Chunking |
| `notebooks/03_embedding.ipynb` | Embedding |
| `notebooks/03_store.ipynb` | Storing |
| `notebooks/04_retrieval.ipynb` | Retrieval |

## SDK Stages

| Stage | Method | Output |
|---|---|---|
| URL ingestion | `rag.scrape(...)` | In-memory markdown outputs |
| URL retry | `rag.scrape(dlq=...)` | Retried in-memory markdown outputs |
| Document ingestion | `rag.parse(...)` | In-memory markdown outputs |
| API ingestion | `rag.fetch(...)` | In-memory markdown outputs |
| Chunking | `rag.chunk(...)` | In-memory chunk dictionaries |
| Single-file chunk preview | `rag.chunk_file(...)` | In-memory chunk dictionaries |
| Embedding | `rag.embed(...)` | Embedded vectors in a vector DB |
| Vector storage | `rag.store(...)` | Alias for embedding and storing chunks |
| Retrieval | `rag.retrieve(...)` | Ranked retrieved chunks |

The usage interfaces are organized in the package under `ragrails/interfaces/`:

```text
ragrails/interfaces/
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

Run local interface checks:

```bash
scripts/test-core.sh
scripts/test-sdk.sh
scripts/test-cli.sh
scripts/test-rest.sh
```

Build and publish with `uv` directly:

```bash
uv build
uv publish
```

## Status

The public SDK currently covers ingestion, chunking, embedding, vector storage,
and retrieval. Chat and eval exist internally and will be exposed as public SDK
surfaces later.
