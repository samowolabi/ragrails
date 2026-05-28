# Chunking

Use `RagRails().chunk()` to split markdown text into RAG-ready chunks.

## Contract

Chunking is data-first. It accepts markdown content directly and returns chunk
dictionaries in memory. It does not require `input_dir` or `output_dir` on the
public SDK surface.

Chunking is responsible for:

- accepting markdown strings or markdown document dictionaries
- preserving source path, title, description, and original type
- splitting content into retrieval-sized chunks
- preserving heading context
- keeping code blocks atomic where possible
- splitting large tables while retaining header context
- repairing links that cross chunk boundaries
- dropping navigation-heavy chunks
- assigning stable chunk IDs and content hashes

## One Markdown Document

```python
from ragrails import RagRails

result = RagRails().chunk(
    markdown="# Guide\n\nUse Ragrails to build a retrieval pipeline.",
    title="Guide",
    source="guide.md",
)

print(result.chunks)
print(result.items)
```

## Multiple Markdown Documents

Pass an array when you want to chunk multiple documents in one call.

```python
from ragrails import RagRails

result = RagRails().chunk(
    markdown=[
        {
            "markdown": "# Auth\n\nUse a bearer token.",
            "title": "Auth",
            "source": "https://docs.example.com/auth",
        },
        {
            "markdown": "# Billing\n\nInvoices are generated monthly.",
            "title": "Billing",
            "source": "https://docs.example.com/billing",
        },
    ],
    chunk_size=1200,
    chunk_overlap=150,
    min_chunk_length=80,
)

for chunk in result.items:
    print(chunk["metadata"]["chunk_id"])
    print(chunk["text"][:300])
```

Each array item can be either a markdown string or a dictionary with:

- `markdown`, `content`, or `text`
- `title`
- `source`
- `metadata`

## From Ingestion Outputs

The normal SDK flow is to pass ingestion outputs directly into chunking:

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

This keeps the SDK data-first: ingestion returns markdown outputs in memory,
and chunking consumes those outputs directly.

## Result

`chunk()` returns a `ChunkResult`:

```python
print(result.inputs)
print(result.chunks)
print(result.items)
print(result.failed)
print(result.errors)
```

Each chunk includes:

- `text`
- `embed_text`
- `metadata.id`
- `metadata.chunk_id`
- `metadata.content_hash`
- `metadata.heading`
- `metadata.source`
- `metadata.title`

Table chunks may also include:

- `metadata.table_id`
- `metadata.columns`
- `metadata.row_start`
- `metadata.row_end`

## Parameters

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `markdown` | `str \| list[str \| dict]` | - | Yes | Markdown text or an array of markdown documents. |
| `title` | `str` | `""` | No | Title metadata applied to plain string markdown inputs. |
| `source` | `str` | `""` | No | Source metadata applied to plain string markdown inputs. |
| `chunk_size` | `int` | `2000` | No | Target maximum chunk size in characters. |
| `chunk_overlap` | `int` | `200` | No | Character overlap between neighboring chunks. |
| `min_chunk_length` | `int` | `100` | No | Minimum chunk length to keep. Shorter chunks are dropped. |

## Validation

`chunk()` raises an error when:

- `markdown` is empty.
- a markdown array item is neither a string nor a dictionary.
- a markdown dictionary does not include `markdown`, `content`, or `text`.
- `chunk_size` is less than `1`.
- `chunk_overlap` is negative.
- `chunk_overlap` is greater than or equal to `chunk_size`.
- `min_chunk_length` is less than `1`.
