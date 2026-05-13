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

stored = rag.store(
    input_dir=chunks.output_dir,
    vector_db="qdrant",
    collection="rag_chunks",
)

print(stored.chunks)
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

stored = rag.store(
    input_dir=chunks.output_dir,
    vector_db="qdrant",
    collection="rag_chunks",
)

print(stored.chunks)
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

Ragrails ships with a CLI so you can run ingestion without writing Python.

```bash
ragrails setup-url
ragrails scrape https://example.com --mode full
ragrails scrape https://example.com/about https://example.com/pricing
ragrails parse --folder files/input
ragrails parse --files guide.pdf --files pricing.csv --input-dir files/input
ragrails fetch https://api.example.com/v1/products --title "Products"
ragrails fetch https://api.example.com/v1/products \
  --header "Authorization:Bearer <token>" \
  --header "X-Api-Key:my-key"
```

See the full [CLI reference](docs/sdk/cli/README.md).

## SDK Stages

| Stage | Method | Output |
|---|---|---|
| URL ingestion | `rag.scrape(...)` | Markdown files |
| URL retry | `rag.retry_scrape(...)` | Retried markdown files |
| Document ingestion | `rag.parse(...)` | Markdown files |
| API ingestion | `rag.fetch(...)` | Markdown files |
| Chunking | `rag.chunk(...)` | JSON chunk files |
| Single-file chunk preview | `rag.chunk_file(...)` | In-memory chunk dictionaries |
| Vector storage | `rag.store(...)` | Embedded vectors in a vector DB |

Hosted documentation:

- [https://dev.ragrails.com](https://dev.ragrails.com)

Repository docs:

- [CLI](docs/sdk/cli/README.md)
- [Ingestion](docs/sdk/01_ingestion/README.md)
- [URL ingestion](docs/sdk/01_ingestion/url/README.md)
- [Document ingestion](docs/sdk/01_ingestion/documents/README.md)
- [API ingestion](docs/sdk/01_ingestion/api/README.md)
- [Chunking](docs/sdk/02_chunking/README.md)
- [Embedding and storage](docs/sdk/03_embedding/README.md)
- [Retrieval](docs/sdk/04_retrieval/README.md)

## Ingestion

### URL Ingestion

```python
result = RagRails().scrape(
    url="https://example.com/about",
    mode="each",
    output_dir="files/output/web_crawled",
)
```

For full-site crawling:

```python
result = RagRails().scrape(
    url="https://example.com",
    mode="full",
    output_dir="files/output/web_crawled",
    max_depth=3,
    max_pages=200,
)
```

Failed URL attempts are written to `dlq.json` inside the output folder by
default:

```text
files/output/web_crawled/dlq.json
```

Retry failed URLs:

```python
result = RagRails().retry_scrape(
    "files/output/web_crawled/dlq.json",
)
```

### Document Ingestion

```python
result = RagRails().parse(
    folder="files/input",
    output_dir="files/output/docs",
)
```

Supported folder discovery extensions:

```text
.csv, .docx, .epub, .html, .htm, .ipynb, .json, .md, .msg,
.pdf, .pptx, .rss, .tsv, .txt, .xls, .xlsx, .xml, .zip
```

### API Ingestion

```python
result = RagRails().fetch(
    url="https://api.example.com/v1/search",
    method="POST",
    headers={
        "Authorization": "Bearer <token>",
        "X-Api-Key": "my-key",
    },
    body={"query": "payments"},
    title="Search Results",
    output_dir="files/output/api",
)
```

## Chunking

```python
result = RagRails().chunk(
    input_dir="files/output/docs",
    output_dir="files/output/chunks/docs",
    chunk_size=2000,
    chunk_overlap=200,
)
```

Preview one markdown file in memory:

```python
chunks = RagRails().chunk_file(
    "files/output/docs/guide.md",
)
```

## Vector Storage

Ragrails currently supports Qdrant, Pinecone, and Weaviate as storage providers.

Set provider credentials as needed:

```bash
export VOYAGE_API_KEY="..."
export PINECONE_API_KEY="..."
export WEAVIATE_API_KEY="..."
```

Qdrant local example:

```bash
docker run -p 6333:6333 qdrant/qdrant
```

```python
result = RagRails().store(
    input_dir="files/output/chunks/docs",
    vector_db="qdrant",
    url="http://localhost:6333",
    collection="rag_chunks",
)
```

Pinecone example:

```python
result = RagRails().store(
    input_dir="files/output/chunks/docs",
    vector_db="pinecone",
    collection="rag-chunks",
)
```

Weaviate example:

```python
result = RagRails().store(
    input_dir="files/output/chunks/docs",
    vector_db="weaviate",
    url="http://localhost:8080",
    collection="RagChunks",
)
```

Provider naming rules:

| Provider | Collection name |
|---|---|
| Qdrant | Any valid Qdrant collection name, for example `rag_chunks` |
| Pinecone | Lowercase letters, digits, and hyphens, for example `rag-chunks` |
| Weaviate | Starts with an uppercase letter, for example `RagChunks` |

## Result Types

```python
ScrapeResult(
    pages=int,
    failed=int,
    output_dir=str,
    files=list[str],
    dlq_path=str,
    errors=list[str],
)
```

```python
ParseResult(
    documents=int,
    failed=int,
    output_dir=str,
    files=list[str],
    errors=list[str],
)
```

```python
ApiIngestResult(
    pages=int,
    items=int,
    failed=int,
    output_dir=str,
    files=list[str],
    errors=list[str],
)
```

```python
ChunkResult(
    files=int,
    chunks=int,
    output_dir=str,
    output_files=list[str],
    failed=int,
    errors=list[str],
)
```

```python
StoreResult(
    files=int,
    chunks=int,
    input_dir=str,
    provider=str,
    collection=str,
    errors=list[str],
)
```

## Parameter Reference

### `setup_url()`

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `browser` | `str` | `"chromium"` | No | Playwright browser binary to install for URL scraping. |

### `scrape()`

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `url` | `str \| list[str]` | - | Yes | URL or URLs to scrape. |
| `mode` | `"each" \| "full"` | `"each"` | No | Scrape exact URLs or crawl full sites. |
| `output_dir` | `str` | `"files/output/web_crawled"` | No | Markdown output folder. |
| `frontmatter` | `bool` | `True` | No | Add source metadata to markdown files. |
| `dlq_path` | `str \| None` | `None` | No | Custom DLQ file. Defaults to `<output_dir>/dlq.json`. |
| `max_depth` | `int` | `3` | No | Crawl depth for `mode="full"`. |
| `max_pages` | `int` | `200` | No | Maximum pages per site. |

### `retry_scrape()`

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `dlq_path` | `str` | - | Yes | DLQ file to retry. |
| `mode` | `"each" \| "full"` | `"each"` | No | Retry as exact pages or full-site crawls. |
| `max_depth` | `int` | `3` | No | Crawl depth for `mode="full"`. |
| `max_pages` | `int` | `200` | No | Maximum pages per site. |
| `max_attempts` | `int` | `3` | No | Retry entries below this attempt count. |

### `parse()`

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `files` | `str \| list[str \| dict] \| None` | `None` | Conditional | Specific files to parse. |
| `folder` | `str \| None` | `None` | Conditional | Folder of supported files to parse. |
| `input_dir` | `str` | `"files/input"` | No | Base folder for `files`. |
| `output_dir` | `str` | `"files/output/docs"` | No | Markdown output folder. |
| `frontmatter` | `bool` | `True` | No | Add document metadata to markdown files. |

### `fetch()`

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `url` | `str` | - | Yes | API endpoint URL. |
| `title` | `str` | `"API Response"` | No | Output metadata title. |
| `description` | `str` | `""` | No | Output metadata description. |
| `method` | `str` | `"GET"` | No | HTTP method. |
| `headers` | `dict \| None` | `None` | No | Request headers. Multiple headers are supported. |
| `params` | `dict \| None` | `None` | No | Query parameters. |
| `body` | `dict \| None` | `None` | No | JSON request body. |
| `pagination` | `dict \| None` | `None` | No | Pagination configuration. |
| `max_pages` | `int` | `100` | No | Maximum API pages to fetch. |
| `output_dir` | `str` | `"files/output/api"` | No | Markdown output folder. |
| `frontmatter` | `bool` | `True` | No | Add API metadata to markdown files. |

### `chunk()`

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `input_dir` | `str` | `"files/output/web_crawled"` | No | Folder containing markdown files. |
| `output_dir` | `str` | `"files/output/chunks"` | No | JSON chunk output folder. |
| `chunk_size` | `int` | `2000` | No | Target maximum chunk size. |
| `chunk_overlap` | `int` | `200` | No | Overlap between chunks. |
| `min_chunk_length` | `int` | `100` | No | Minimum chunk length to keep. |

### `chunk_file()`

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `path` | `str` | - | Yes | Markdown file path to chunk in memory. |
| `chunk_size` | `int` | `2000` | No | Target maximum chunk size. |
| `chunk_overlap` | `int` | `200` | No | Overlap between chunks. |
| `min_chunk_length` | `int` | `100` | No | Minimum chunk length to keep. |

### `store()`

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `input_dir` | `str` | `"files/output/chunks"` | No | Folder of chunk JSON files. |
| `vector_db` | `"qdrant" \| "pinecone" \| "weaviate"` | `"qdrant"` | No | Vector database provider. |
| `collection` | `str \| None` | `None` | No | Collection, index, or class name. |
| `url` | `str \| None` | `None` | No | Vector database URL. |
| `files` | `str \| list[str] \| None` | `None` | No | Selected chunk files to store. |
| `batch_size` | `int` | `64` | No | Chunks per embedding/storage batch. |
| `embedder` | `str` | `"voyage"` | No | Embedding provider. |
| `model` | `str` | `"voyage-3"` | No | Embedding model name. |

## Status

The public SDK currently covers ingestion, chunking, and vector storage.
Retrieval, chat, and eval exist internally and will be exposed as public SDK
surfaces next.
