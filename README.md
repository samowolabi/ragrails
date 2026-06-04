# Ragrails

[![PyPI](https://img.shields.io/pypi/v/ragrails)](https://pypi.org/project/ragrails/)
[![Python](https://img.shields.io/pypi/pyversions/ragrails)](https://pypi.org/project/ragrails/)
[![Downloads](https://static.pepy.tech/badge/ragrails)](https://pepy.tech/project/ragrails)
[![License](https://img.shields.io/pypi/l/ragrails)](LICENSE)

Ragrails is a modular RAG toolkit for turning URLs, local documents, and REST
API responses into retrieval-ready vector indexes.

It is organized in layers:

```text
core -> SDK -> CLI -> REST API
```

Most users should use the SDK, CLI, or REST API. The core modules are the shared
foundation that the public interfaces build on.

## Install

Ragrails requires Python 3.10 or newer.

```bash
pip install ragrails
```

The base install includes the SDK, CLI, REST API server, document ingestion, API
ingestion, chunking, embedding orchestration, vector storage orchestration,
retrieval, chat orchestration, and pipeline helpers.

Install extras for URL scraping, model providers, reranking, and vector database
clients:

| Need | Install |
|---|---|
| URL ingestion | `pip install "ragrails[url]"` |
| Store in Qdrant | `pip install "ragrails[store-qdrant]"` |
| Store in Pinecone | `pip install "ragrails[store-pinecone]"` |
| Store in Weaviate | `pip install "ragrails[store-weaviate]"` |
| REST API with Qdrant stack | `pip install "ragrails[server-qdrant]"` |
| REST API with Pinecone stack | `pip install "ragrails[server-pinecone]"` |
| REST API with Weaviate stack | `pip install "ragrails[server-weaviate]"` |
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

## SDK Quick Start

```python
from ragrails import RagRails

rag = RagRails()
```

### Ingest and Store

Run ingestion, chunking, embedding, and vector storage in one call:

```python
from ragrails import RagRails

rag = RagRails()

result = rag.ingest(
    markdown="# Guide\n\nRagrails builds modular RAG workflows.",
    embedding={
        "provider": "voyage",
        "model": "voyage-3",
    },
    storage={
        "vector_db": "qdrant",
        "collection": "docs",
        "url": "http://localhost:6333",
    },
)

print(result.stored)
```

You can also provide `docs`, `urls`, or `api` sources:

```python
rag.ingest(
    docs=["files/guide.pdf"],
    ingestion={"docs": {"mode": "single"}},
    embedding={"provider": "voyage", "model": "voyage-3"},
    storage={"vector_db": "qdrant", "collection": "docs"},
)
```

URL ingestion uses Playwright through `crawl4ai`. Install the URL extra and run
browser setup once in the target environment:

```bash
pip install "ragrails[url,voyage,qdrant]"
```

```python
RagRails().setup_url()
```

### Query

Run query embedding and retrieval in one call:

```python
result = rag.query(
    "What does the guide cover?",
    embedding={
        "provider": "voyage",
        "model": "voyage-3",
    },
    retrieval={
        "vector_db": "qdrant",
        "collection": "docs",
        "url": "http://localhost:6333",
        "top_k": 5,
    },
)

for chunk in result.items:
    print(chunk.text)
```

### Chat

Chat is stateless. Pass `history` explicitly and persist the returned
`result.history` in your app session.

```python
from ragrails import QueryRewriteConfig, RagRails

rag = RagRails()

llm = rag.llm(provider="openai", model="gpt-4.1-mini")
embedder = rag.embedder(provider="voyage", model="voyage-3", input_type="query")

history = []

result = rag.chat(
    "How do I authenticate?",
    llm=llm,
    embedder=embedder,
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
    history=history,
    query_rewrite=QueryRewriteConfig(enabled=True),
)

print(result.answer)
history = result.history
```

### Edit and Delete Stored Chunks

Edit and delete operations are vector database agnostic at the SDK layer.

```python
edit_result = rag.edit(
    chunks=[
        {
            "id": "chunk-id",
            "text": "Updated chunk text",
            "source": "files/guide.pdf",
            "metadata": {"title": "Guide"},
        }
    ],
    embedder=rag.embedder(provider="voyage", model="voyage-3"),
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
)

delete_result = rag.delete(
    ids=["chunk-id"],
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
)
```

## CLI

Ragrails ships with a CLI for local workflows and smoke tests.

```bash
ragrails --help
```

Examples:

```bash
ragrails ingest \
  --markdown "# Guide\n\nUse Ragrails for RAG workflows." \
  --vector-db qdrant \
  --collection docs
```

```bash
ragrails query "What does the guide cover?" \
  --vector-db qdrant \
  --collection docs
```

CLI docs live in [ragrails/interfaces/cli/README.md](ragrails/interfaces/cli/README.md).

## REST API

Ragrails ships a FastAPI server on top of the SDK.

```bash
ragrails-api
```

Swagger UI is available at `http://127.0.0.1:8000/docs` when the server is
running. The OpenAPI schema is available at `/v1/openapi.json`.

REST docs live in
[ragrails/interfaces/server/README.md](ragrails/interfaces/server/README.md).

## Package Structure

```text
ragrails/
  core/
    stg_01_ingestors/
    stg_02_chunker/
    stg_03_embedder/
    stg_04_storing/
    stg_05_retriever/
    stg_06_chat/
  interfaces/
    sdk/
    cli/
    server/
```

## Interface Docs

| Interface | Docs |
|---|---|
| SDK chunking | [ragrails/interfaces/sdk/chunking/README.md](ragrails/interfaces/sdk/chunking/README.md) |
| SDK embedding | [ragrails/interfaces/sdk/embedding/README.md](ragrails/interfaces/sdk/embedding/README.md) |
| SDK storing | [ragrails/interfaces/sdk/storing/README.md](ragrails/interfaces/sdk/storing/README.md) |
| SDK retrieval | [ragrails/interfaces/sdk/retrieval/README.md](ragrails/interfaces/sdk/retrieval/README.md) |
| SDK chat | [ragrails/interfaces/sdk/chat/README.md](ragrails/interfaces/sdk/chat/README.md) |
| CLI | [ragrails/interfaces/cli/README.md](ragrails/interfaces/cli/README.md) |
| REST API | [ragrails/interfaces/server/README.md](ragrails/interfaces/server/README.md) |

Specialized SDK ingestion docs:

- [URL ingestion](ragrails/interfaces/sdk/ingestion/url/README.md)
- [Document ingestion](ragrails/interfaces/sdk/ingestion/docs/README.md)
- [API ingestion](ragrails/interfaces/sdk/ingestion/api/README.md)

## Development Checks

Run local interface checks:

```bash
scripts/test-core.sh
scripts/test-sdk.sh
scripts/test-cli.sh
scripts/test-rest.sh
```

The repo uses `.githooks/pre-push`, so `git push` runs the same checks and
blocks the push if any interface test fails.

Build and validate release artifacts:

```bash
uv build
uvx twine check dist/*
```

Publish only after the checks pass:

```bash
uv publish
```

## Status

The public SDK currently covers ingestion, chunking, embedding, vector storage,
retrieval, chat, vector edit/delete, and end-to-end ingestion/query pipeline
helpers. CLI and REST API interfaces are built on top of the SDK.
