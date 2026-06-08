# Ragrails

[![PyPI](https://img.shields.io/pypi/v/ragrails)](https://pypi.org/project/ragrails/)
[![Python](https://img.shields.io/pypi/pyversions/ragrails)](https://pypi.org/project/ragrails/)
[![Downloads](https://static.pepy.tech/badge/ragrails)](https://pepy.tech/project/ragrails)
[![License](https://img.shields.io/pypi/l/ragrails)](LICENSE)

Ragrails is a modular Python toolkit for building RAG (Retrieval-Augmented Generation) pipelines. It turns URLs, local documents, and REST API responses into retrieval-ready vector indexes, and provides retrieval and chat on top.

```
core → SDK → CLI / REST API
```

---

## Contents

- [Install](#install)
- [Quick Start](#quick-start)
- [SDK](#sdk)
  - [Ingestion](#ingestion)
  - [Chunking](#chunking)
  - [Embedding](#embedding)
  - [Storing](#storing)
  - [Retrieval](#retrieval)
  - [Chat](#chat)
  - [Pipeline helpers](#pipeline-helpers)
- [CLI](#cli)
- [REST API](#rest-api)
- [Development](#development)

---

## Install

Requires Python 3.10 or newer.

```bash
pip install ragrails
```

Install extras for URL scraping, embedding providers, reranking, and vector
database clients. OpenAI, Anthropic, and Google Gemini LLM providers are
included in the base install.

| Need | Install |
|---|---|
| URL ingestion | `pip install "ragrails[url]"` |
| Voyage embeddings | `pip install "ragrails[voyage]"` |
| Qdrant | `pip install "ragrails[qdrant]"` |
| Pinecone | `pip install "ragrails[pinecone]"` |
| Weaviate | `pip install "ragrails[weaviate]"` |
| Reranking | `pip install "ragrails[rerank]"` |
| SDK + Qdrant stack | `pip install "ragrails[store-qdrant]"` |
| REST API + Qdrant stack | `pip install "ragrails[server-qdrant]"` |
| REST API + Pinecone stack | `pip install "ragrails[server-pinecone]"` |
| REST API + Weaviate stack | `pip install "ragrails[server-weaviate]"` |
| Everything | `pip install "ragrails[all]"` |

---

## Quick Start

```python
from ragrails import RagRails

rag = RagRails(
    collection="docs",
    vector_store={"provider": "qdrant", "url": "http://localhost:6333"},
    embedding={"provider": "voyage", "model": "voyage-3"},
    llm={"provider": "openai", "model": "gpt-5.5"},
)

# Ingest a document and store it
rag.ingest(docs=["files/guide.pdf"])

# Query it
result = rag.query("What does the guide cover?")

for chunk in result.items:
    print(chunk.text)
```

---

## SDK

### Ingestion

Three ingestors produce normalized document dicts with `id`, `text`, `source`, and `metadata` fields.

**URL — `scrape()`**

Requires `pip install "ragrails[url]"`. Run browser setup once:

```python
rag.setup_url()  # installs Playwright chromium
```

```python
# Single URL
result = rag.scrape("https://example.com/docs")

# Full site crawl
result = rag.scrape("https://example.com", mode="full", max_depth=2, max_pages=50)

# Multiple URLs with per-URL config
result = rag.scrape([
    "https://example.com/docs",
    {"url": "https://example.com/blog", "mode": "full", "max_depth": 1},
])

result.pages    # pages scraped
result.outputs  # list of document dicts
result.errors   # list of error dicts
```

Use a dead-letter queue to capture and retry failed pages:

```python
from ragrails import DLQ

result = rag.scrape("https://example.com", mode="full", dlq=DLQ("files/dlq/web.json"))
# retry
result = rag.scrape(dlq=result.dlq)
```

**Documents — `parse()`**

Supports PDF, DOCX, PPTX, XLSX, HTML, Markdown, TXT, CSV, and more.

```python
# Single file
result = rag.parse(files=["files/guide.pdf"])

# Folder of documents
result = rag.parse(folder="files/docs/")

result.documents  # documents parsed
result.outputs    # list of document dicts
```

**REST API — `fetch()`**

```python
result = rag.fetch(
    url="https://api.example.com/posts",
    title="Blog posts",
    headers={"Authorization": "Bearer token"},
    pagination={"type": "page", "param": "page", "size_param": "per_page", "size": 100},
    max_pages=10,
)

# Multiple endpoints
result = rag.fetch(apis=[
    {"url": "https://api.example.com/posts", "title": "Posts"},
    {"url": "https://api.example.com/comments", "title": "Comments"},
])
```

**Saving ingestion output to disk**

All ingestors support `output_dest="file"` to save results as JSON files:

```python
result = rag.scrape(
    "https://example.com/docs",
    output_format="json",
    output_dest="file",
    output_dir="files/output/web/",
)
result.outputs[0]["output_path"]  # "files/output/web/001_docs.json"
```

---

### Chunking

`chunk()` splits markdown documents into stable, embedding-ready pieces.

```python
result = rag.chunk(
    markdown=result.outputs,   # list of dicts with a "text" key, or plain strings
    chunk_size=2000,
    chunk_overlap=200,
    min_chunk_length=100,
)

result.inputs  # documents passed in
result.chunks  # chunks produced
result.items   # list of chunk dicts — each has id, text, source, metadata
```

---

### Embedding

Configured clients create the embedder automatically.

```python
result = rag.embed(chunks=result.items, batch_size=64)

result.embedded  # chunks successfully embedded
result.items     # chunk dicts with an added "embedding" vector field
result.errors    # list of error dicts
```

Supported provider: `voyage` (`voyage-3`, `voyage-3-lite`, `voyage-3-large`).

---

### Storing

Store embedded chunks in a vector database. `store()` creates the collection automatically if it does not exist.

```python
result = rag.store(
    embedded_chunks=result.items,
)

result.stored      # chunks upserted
result.provider    # vector DB provider
result.collection  # collection name
```

**Edit and delete**

```python
# Re-embed and replace chunks by ID
edit_result = rag.edit(
    chunks=[{"id": "chunk-id", "text": "Updated text", "source": "...", "metadata": {}}],
)

# Delete chunks by ID
delete_result = rag.delete(
    ids=["chunk-id-1", "chunk-id-2"],
)
```

Supported databases: `qdrant`, `qdrant_cloud`, `pinecone`, `weaviate`.

For Qdrant Cloud, use `provider="qdrant_cloud"` with your cluster URL and set
`QDRANT_API_KEY` in your environment.

---

### Retrieval

Configured clients create the query embedder and vector store automatically.

```python
result = rag.retrieve(
    "How do I authenticate?",
    top_k=10,
)

for chunk in result.items:
    print(chunk.score, chunk.text)
```

**With reranking**

```python
result = rag.retrieve(
    "How do I authenticate?",
    use_rerank=True,
    rerank_top_k=5,
)
```

**With query rewriting**

```python
result = rag.retrieve(
    "What about the second step?",
    use_query_rewrite=True,
    session_context="User is asking about the onboarding flow.",
)

result.search_query  # rewritten query used for search
```

---

### Chat

Chat is stateless. Pass `history` in and persist `result.history` in your application.

```python
from ragrails import QueryRewriteConfig, RagRails

history = []

result = rag.chat(
    "How do I authenticate?",
    history=history,
)

print(result.answer)
history = result.history  # pass to the next turn
```

**Config objects**

```python
from ragrails import (
    ChatRetrievalQualityConfig,
    HistoryCompactionConfig,
    IntentRoutingConfig,
    QueryRewriteConfig,
)

result = rag.chat(
    "What about the second step?",
    history=history,
    query_rewrite=QueryRewriteConfig(enabled=True, session_context="Onboarding flow"),
    history_compaction=HistoryCompactionConfig(enabled=True, history_limit=15, keep_recent=5),
    intent_routing=IntentRoutingConfig(enabled=True),
    retrieval_quality=ChatRetrievalQualityConfig(min_retrieval_score=0.35, min_rerank_score=0.50),
    persona="You are a helpful onboarding assistant.",
)

result.answer             # LLM answer
result.sources            # source chunks used
result.history            # updated history
result.intent             # "rag" or "direct"
result.answer_confidence  # confidence assessment dict
result.compacted          # True if history was summarised this turn
```

---

### Pipeline Helpers

`ingest()` and `query()` are convenience wrappers that run multiple SDK stages in one call.

```python
# Full pipeline: ingest → chunk → embed → store
result = rag.ingest(
    docs=["files/guide.pdf"],
    concurrency="serial",
)

result.sources   # source documents ingested
result.chunks    # chunks produced
result.embedded  # chunks embedded
result.stored    # chunks stored

# Query pipeline: embed query → retrieve
result = rag.query(
    "What does the guide cover?",
    retrieval={
        "top_k": 5,
        "rerank": {"enabled": True, "provider": "voyage", "top_k": 3},
    },
)
```

Sources accepted by `ingest()`: `docs`, `urls`, `api`, `markdown`. All can be combined in one call.
Use `concurrency="parallel"` to run independent source ingestion groups at the
same time before chunking, embedding, and storage.

---

## CLI

```bash
ragrails
ragrails --help
```

Running `ragrails` with no subcommand starts the project setup wizard. Quick
setup writes core defaults to `.ragrails.toml` in the current folder:

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

Advanced setup can also add practical stage defaults:

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

CLI commands use this file as defaults. Command flags override config for one
run. API keys are not written to config; set them with environment variables
such as `VOYAGE_API_KEY` and `OPENAI_API_KEY`.

Run `ragrails doctor` to validate your config, installed provider packages, API
keys, and (with `--connections`) vector database reachability. It supports
`--json` output for CI.

### Stage commands

Run pipeline stages one at a time, passing output between them as JSON files.

```bash
# Ingest
ragrails scrape https://example.com/docs --output-dir files/output/web/
ragrails parse --folder files/docs/ --output-dir files/output/docs/
ragrails fetch https://api.example.com/posts --output-dir files/output/api/

# Chunk
ragrails chunk --input-dir files/output/docs/ --output-dir files/chunks/

# Embed
ragrails embed \
  --input-dir files/chunks/ \
  --output-dir files/embedded/

# Store
ragrails store \
  --input-dir files/embedded/

# Edit and delete
ragrails edit --input-dir files/updated/
ragrails delete --id chunk-id-1 --id chunk-id-2

# Retrieve
ragrails retrieve "How do I authenticate?"
```

### Pipeline commands

Run the full pipeline in one command:

```bash
ragrails ingest \
  --docs files/guide.pdf

ragrails query "What does the guide cover?" \
  --vector-db qdrant \
  --collection other_docs \
  --rerank
```

### Chat

One-shot chat turn:

```bash
ragrails chat "How do I authenticate?"
```

Stateless multi-turn with a history file:

```bash
ragrails chat "How do I authenticate?" --history-file files/chat/history.json
ragrails chat "What about the second step?" --history-file files/chat/history.json --rewrite-query
```

Interactive REPL (no query argument):

```bash
ragrails chat
```

URL setup:

```bash
ragrails setup-url
```

---

## REST API

Start the server:

```bash
pip install "ragrails[server-qdrant]"
ragrails-api
```

Swagger UI: `http://127.0.0.1:8000/docs`

Run with Docker:

```bash
cp docker/env/api.env.example docker/env/api.env
docker compose -f docker/compose/compose.yaml --env-file docker/env/api.env up --build
```

See [docker/README.md](docker/README.md) for API container, Qdrant, logs, and production notes.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/v1/health` | Health check |
| POST | `/v1/ingest/url` | Scrape URLs |
| POST | `/v1/ingest/url/stream` | Stream URL scraping progress |
| POST | `/v1/ingest/docs` | Parse documents |
| POST | `/v1/ingest/api` | Fetch REST APIs |
| POST | `/v1/chunk` | Chunk documents |
| POST | `/v1/embed` | Embed chunks |
| POST | `/v1/store` | Store embedded chunks |
| POST | `/v1/edit` | Edit stored chunks |
| POST | `/v1/delete` | Delete stored chunks |
| POST | `/v1/retrieve` | Retrieve chunks |
| POST | `/v1/pipelines/ingest` | Full ingest pipeline |
| POST | `/v1/pipelines/query` | Query pipeline |
| POST | `/v1/chat` | RAG chat turn |
| POST | `/v1/chat/stream` | Stream RAG chat progress and tokens |

---

## Development

Run tests by interface layer:

```bash
scripts/test-core.sh
scripts/test-sdk.sh
scripts/test-cli.sh
scripts/test-rest.sh
```

The repo uses a pre-push hook (`.githooks/pre-push`) that runs all checks automatically before each push.

Build and validate release artifacts:

```bash
uv build
uvx twine check dist/*
```

Publish:

```bash
uv publish
```
