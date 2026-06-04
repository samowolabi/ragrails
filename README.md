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

Install extras for URL scraping, model providers, and vector database clients:

| Need | Install |
|---|---|
| URL ingestion | `pip install "ragrails[url]"` |
| Voyage embeddings | `pip install "ragrails[voyage]"` |
| OpenAI | `pip install "ragrails[openai]"` |
| Anthropic | `pip install "ragrails[anthropic]"` |
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

rag = RagRails()

# Ingest a document and store it
rag.ingest(
    docs=["files/guide.pdf"],
    embedding={"provider": "voyage", "model": "voyage-3"},
    storage={"vector_db": "qdrant", "collection": "docs", "url": "http://localhost:6333"},
)

# Query it
result = rag.query(
    "What does the guide cover?",
    embedding={"provider": "voyage", "model": "voyage-3"},
    retrieval={"vector_db": "qdrant", "collection": "docs", "url": "http://localhost:6333"},
)

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
    pagination={"type": "page", "page_param": "page", "page_size": 100},
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

Create an embedder object, then pass it to `embed()`.

```python
embedder = rag.embedder(provider="voyage", model="voyage-3", input_type="document")

result = rag.embed(chunks=result.items, embedder=embedder, batch_size=64)

result.embedded  # chunks successfully embedded
result.items     # chunk dicts with an added "embedding" vector field
result.errors    # list of error dicts
```

Supported providers: `voyage`, `openai`.

---

### Storing

Store embedded chunks in a vector database. `store()` creates the collection automatically if it does not exist.

```python
result = rag.store(
    embedded_chunks=result.items,
    vector_db="qdrant",         # "qdrant", "pinecone", or "weaviate"
    collection="docs",
    url="http://localhost:6333",
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
    embedder=rag.embedder(provider="voyage", model="voyage-3"),
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
)

# Delete chunks by ID
delete_result = rag.delete(
    ids=["chunk-id-1", "chunk-id-2"],
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
)
```

Supported databases: `qdrant`, `pinecone`, `weaviate`.

---

### Retrieval

Create an embedder with `input_type="query"`, then retrieve.

```python
embedder = rag.embedder(provider="voyage", model="voyage-3", input_type="query")

result = rag.retrieve(
    "How do I authenticate?",
    embedder=embedder,
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
    top_k=10,
)

for chunk in result.items:
    print(chunk.score, chunk.text)
```

**With reranking**

```python
reranker = rag.reranker(provider="voyage", model="rerank-2-lite")

result = rag.retrieve(
    "How do I authenticate?",
    embedder=embedder,
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
    use_rerank=True,
    reranker=reranker,
    rerank_top_k=5,
)
```

**With query rewriting**

```python
rewrite_llm = rag.llm(provider="openai", model="gpt-4.1-mini")

result = rag.retrieve(
    "What about the second step?",
    embedder=embedder,
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
    use_query_rewrite=True,
    rewrite_llm=rewrite_llm,
    session_context="User is asking about the onboarding flow.",
)

result.search_query  # rewritten query used for search
```

---

### Chat

Chat is stateless. Pass `history` in and persist `result.history` in your application.

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
    llm=llm,
    embedder=embedder,
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
    history=history,
    reranker=rag.reranker(provider="voyage", model="rerank-2-lite"),
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
    embedding={"provider": "voyage", "model": "voyage-3"},
    storage={"vector_db": "qdrant", "collection": "docs", "url": "http://localhost:6333"},
)

result.sources   # source documents ingested
result.chunks    # chunks produced
result.embedded  # chunks embedded
result.stored    # chunks stored

# Query pipeline: embed query → retrieve
result = rag.query(
    "What does the guide cover?",
    embedding={"provider": "voyage", "model": "voyage-3"},
    retrieval={
        "vector_db": "qdrant",
        "collection": "docs",
        "url": "http://localhost:6333",
        "top_k": 5,
        "rerank": {"enabled": True, "provider": "voyage", "top_k": 3},
    },
)
```

Sources accepted by `ingest()`: `docs`, `urls`, `api`, `markdown`. All can be combined in one call.

---

## CLI

```bash
ragrails --help
```

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
  --output-dir files/embedded/ \
  --provider voyage \
  --model voyage-3

# Store
ragrails store \
  --input-dir files/embedded/ \
  --vector-db qdrant \
  --collection docs \
  --url http://localhost:6333

# Edit and delete
ragrails edit --input-dir files/updated/ --vector-db qdrant --collection docs --url http://localhost:6333
ragrails delete --id chunk-id-1 --id chunk-id-2 --vector-db qdrant --collection docs --url http://localhost:6333

# Retrieve
ragrails retrieve "How do I authenticate?" \
  --vector-db qdrant \
  --collection docs \
  --url http://localhost:6333 \
  --provider voyage \
  --model voyage-3
```

### Pipeline commands

Run the full pipeline in one command:

```bash
ragrails ingest \
  --docs files/guide.pdf \
  --vector-db qdrant \
  --collection docs \
  --url http://localhost:6333 \
  --provider voyage \
  --model voyage-3

ragrails query "What does the guide cover?" \
  --vector-db qdrant \
  --collection docs \
  --url http://localhost:6333 \
  --provider voyage \
  --model voyage-3 \
  --rerank
```

### Chat

One-shot chat turn:

```bash
ragrails chat "How do I authenticate?" \
  --vector-db qdrant \
  --collection docs \
  --url http://localhost:6333 \
  --llm-provider openai \
  --llm-model gpt-4.1-mini
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

| Method | Endpoint | Description |
|---|---|---|
| GET | `/v1/health` | Health check |
| POST | `/v1/ingest/url` | Scrape URLs |
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
