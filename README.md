# Ragrails

Ragrails is a staged RAG pipeline for turning web documentation into clean
markdown, then preparing it for chunking, embedding, retrieval, chat, and eval.

The public SDK starts with a simple class-based API:

```python
from ragrails import RagRails

rag = RagRails()
```

Right now the first polished SDK methods are ingestion methods:

```python
result = rag.scrape(
    url="https://example.com/docs",
    mode="full",
    output_dir="files/output/web_crawled",
)
```

The SDK is documented by pipeline stage:

1. [Ingestion](docs/sdk/01_ingestion/README.md)
   - [URL ingestion](docs/sdk/01_ingestion/url/README.md)
   - [Document ingestion](docs/sdk/01_ingestion/documents/README.md)
   - [API ingestion](docs/sdk/01_ingestion/api/README.md)
2. [Chunking](docs/sdk/03_chunking/README.md)
3. [Embedding](docs/sdk/04_embedding/README.md)
4. [Retrieval](docs/sdk/05_retrieval/README.md)

## Requirements

For URL ingestion, install the project dependencies and make sure Playwright's
browser dependencies are available through `crawl4ai`.

Later stages use model providers, so set the API keys needed by the stages you
run:

```bash
export VOYAGE_API_KEY="..."
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

For embedding and retrieval, Qdrant must be running:

```bash
docker run -p 6333:6333 qdrant/qdrant
```

## Quick Start: Scrape One Page

Use `mode="each"` when you want to scrape only the exact URL or URLs you pass.

```python
from ragrails import RagRails

rag = RagRails()

result = rag.scrape(
    url="https://example.com/docs/auth",
    mode="each",
    output_dir="files/output/web_crawled",
)

print(result.pages)
print(result.files)
```

```python
result = rag.parse(
    folder="files/input",
    output_dir="files/output/docs",
)
```

```python
result = rag.fetch(
    url="https://api.example.com/v1/products",
    title="Products",
    output_dir="files/output/api",
)
```

## Crawl a Documentation Site

Use `mode="full"` when you want Ragrails to crawl the site from the starting
URL. Crawling stays domain-scoped and respects `max_depth` and `max_pages`.

```python
from ragrails import RagRails

rag = RagRails()

result = rag.scrape(
    url="https://example.com/docs",
    mode="full",
    output_dir="files/output/web_crawled",
    max_depth=3,
    max_pages=200,
)

print(result.pages)
print(result.files)
```

## Scrape Multiple Exact URLs

```python
from ragrails import RagRails

result = RagRails().scrape(
    url=[
        "https://example.com/docs/auth",
        "https://example.com/docs/payments",
    ],
    mode="each",
    output_dir="files/output/web_crawled",
)
```

## Ingest Local Documents

Use `parse()` to convert local files into markdown. PDF files use
`pymupdf4llm` first and fall back to `markitdown`; other supported document
types use `markitdown`.

```python
from ragrails import RagRails

result = RagRails().parse(
    folder="files/input",
    output_dir="files/output/docs",
)

print(result.documents)
print(result.files)
```

You can provide custom metadata per document:

```python
result = RagRails().parse(
    files=[
        {
            "filename": "guide.pdf",
            "title": "Product Guide",
            "description": "Internal product documentation.",
        },
        {
            "filename": "pricing.csv",
            "title": "Pricing Table",
            "description": "Current product pricing.",
        },
    ],
    input_dir="files/input",
    output_dir="files/output/docs",
)
```

## Fetch an API

Use `fetch()` to convert REST API responses into markdown. Each fetched API
page is written as its own markdown file.

```python
from ragrails import RagRails

result = RagRails().fetch(
    url="https://api.example.com/v1/products",
    title="Products",
    description="Product catalog from the API.",
    output_dir="files/output/api",
)

print(result.pages)
print(result.items)
print(result.files)
```

Disable frontmatter when you want only the converted markdown body:

```python
result = RagRails().parse(
    files=["guide.pdf"],
    frontmatter=False,
)
```

## Output

URL scraping writes markdown files to `output_dir`:

```text
files/output/web_crawled/
  001_index.md
  002_auth.md
  003_payments.md
```

Document ingestion writes markdown files to its own `output_dir`:

```text
files/output/docs/
  guide.md
  pricing.md
```

API ingestion writes markdown files to its own `output_dir`:

```text
files/output/api/
  001_api_example_com_v1_products.md
```

By default, each markdown file starts with Ragrails frontmatter metadata:

```text
path: "https://example.com/docs"
title: "Example Docs"
description: "..."
status_code: "200"
crawled_at: "..."
original_type: "web"
```

Disable frontmatter when you want only the cleaned markdown body:

```python
result = RagRails().scrape(
    url="https://example.com/docs",
    mode="each",
    frontmatter=False,
)
```

## Return Value

`scrape()` returns a `ScrapeResult`:

```python
print(result.pages)       # number of pages written
print(result.failed)      # number of failed pages
print(result.output_dir)  # output directory used
print(result.files)       # markdown files written
print(result.dlq_path)    # dead-letter queue path
print(result.errors)      # crawl/browser errors, if any
```

`parse()` returns a `ParseResult`:

```python
print(result.documents)   # number of documents written
print(result.failed)      # number of failed documents
print(result.output_dir)  # output directory used
print(result.files)       # markdown files written
print(result.errors)      # conversion errors, if any
```

`fetch()` returns an `ApiIngestResult`:

```python
print(result.pages)       # API pages written
print(result.items)       # extracted item count
print(result.failed)      # failed API fetches
print(result.output_dir)  # output directory used
print(result.files)       # markdown files written
print(result.errors)      # API request/conversion errors, if any
```

## API

```python
RagRails().scrape(
    url,
    *,
    mode="each",
    output_dir="files/output/web_crawled",
    frontmatter=True,
    dlq_path="files/output/dlq.json",
    max_depth=3,
    max_pages=200,
)
```

```python
RagRails().parse(
    files=None,
    *,
    folder=None,
    input_dir="files/input",
    output_dir="files/output/docs",
    frontmatter=True,
)
```

```python
RagRails().fetch(
    url,
    *,
    title="API Response",
    description="",
    method="GET",
    headers=None,
    params=None,
    body=None,
    pagination=None,
    max_pages=100,
    output_dir="files/output/api",
    frontmatter=True,
)
```

Modes:

- `each`: scrape only the exact URL or URLs provided.
- `full`: crawl the site from the starting URL.

## Current SDK Entry Point

```python
from ragrails import RagRails
```

## Project Status

The ingestion SDK is being finalized first. Chunking, embedding, retrieval,
chat, and eval already exist internally, and their public SDK names will be
added as the interface is cleaned up.
# ragrails
