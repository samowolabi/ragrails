# SDK Chunking

Use `RagRails().chunk()` to split markdown documents into RAG-ready chunks.

Chunking is response-first. It accepts markdown content in memory and returns
chunk dictionaries in memory. It does not read or write files.

## From Ingestion Outputs

The normal SDK flow is:

```python
from ragrails import RagRails

rag = RagRails()

parsed = rag.parse(files="docs/report.pdf")
chunks = rag.chunk(markdown=parsed.outputs)
```

The same pattern works for URL and API ingestion:

```python
scraped = rag.scrape(url="https://docs.example.com", mode="full")
chunks = rag.chunk(markdown=scraped.outputs)

api_docs = rag.fetch(url="https://api.example.com/products", title="Products")
chunks = rag.chunk(markdown=api_docs.outputs)
```

## Direct Markdown

```python
chunks = rag.chunk(
    markdown="# Guide\n\nUse Ragrails to build a retrieval pipeline.",
    title="Guide",
    source="guide.md",
)
```

## Multiple Documents

```python
chunks = rag.chunk(
    markdown=[
        {
            "text": "# Auth\n\nUse a bearer token.",
            "title": "Auth",
            "source": "https://docs.example.com/auth",
            "metadata": {"source_kind": "docs"},
        },
        {
            "text": "# Billing\n\nInvoices are generated monthly.",
            "title": "Billing",
            "source": "https://docs.example.com/billing",
        },
    ],
    chunk_size=1200,
    chunk_overlap=150,
    min_chunk_length=80,
)
```

Each document can be a string or a dictionary with `text`, plus optional
`source`, `title`, and `metadata`.

## Result

```python
chunks.inputs
chunks.chunks
chunks.items
chunks.failed
chunks.errors
```

Each chunk includes `id`, `text`, `embed_text`, `source`, and `metadata`.
