# URL Ingestion — `scrape()`

Scrape exact URLs or crawl full sites and return each page as a markdown or JSON document.

## Basic usage

```python
from ragrails import RagRails

rag = RagRails()

# Setup (run once)
rag.setup_url()

# Single URL
result = rag.scrape("https://example.com/docs")

# Multiple URLs
result = rag.scrape(["https://example.com/docs", "https://example.com/blog"])

# Full site crawl
result = rag.scrape("https://example.com", mode="full", max_depth=2, max_pages=50)
```

## Per-URL config

Pass a list of dicts to configure each URL individually:

```python
result = rag.scrape([
    "https://example.com/docs",
    {
        "url": "https://example.com/blog",
        "mode": "full",
        "max_depth": 2,
        "max_pages": 50,
    },
])
```

## Frontmatter

Add YAML frontmatter to markdown outputs with `frontmatter=True`. Ignored when `output_format="json"`.

```python
result = rag.scrape("https://example.com/docs", frontmatter=True)
print(result.outputs[0]["text"])
# ---
# title: "Docs"
# source: "https://example.com/docs"
# id: "url_abc123"
# ---
#
# # Page content...
```

## Output format

| `output_format` | Description |
|---|---|
| `"markdown"` | Page content as markdown text (default) |
| `"json"` | Full structured output — text, title, source, metadata |

```python
# Markdown (default)
result = rag.scrape("https://example.com/docs")
result.outputs[0]["text"]   # markdown string

# JSON
result = rag.scrape("https://example.com/docs", output_format="json")
result.outputs[0]           # {"id", "title", "text", "source", "metadata", ...}
```

## Output destination

| `output_dest` | Description |
|---|---|
| `"response"` | Returns result in memory (default) |
| `"file"` | Saves to disk — requires `output_dir` |

```python
# Save as .md files
rag.scrape("https://example.com/docs", output_dest="file", output_dir="files/output/web")

# Save as .json files
rag.scrape("https://example.com/docs", output_format="json", output_dest="file", output_dir="files/output/web")

# Save with frontmatter
rag.scrape("https://example.com/docs", frontmatter=True, output_dest="file", output_dir="files/output/web")

# Access saved path
result = rag.scrape("https://example.com/docs", output_dest="file", output_dir="files/output/web")
result.outputs[0]["output_path"]   # "files/output/web/001_docs.md"
```

## Dead-letter queue (DLQ)

Pages that fail scraping are collected in a DLQ so they can be retried later. Useful for large crawls where some pages time out or fail intermittently.

```python
from ragrails import RagRails, DLQ
```

| `dlq` value | Behaviour |
|---|---|
| `DLQ()` | Collect retryable failures in memory |
| `DLQ("files/dlq/web.json")` | Collect failures in memory and save to file |
| `result.dlq` | Retry failures from a previous result |
| `"files/dlq/web.json"` | Retry failures from a saved file |

```python
# Collect in response
result = rag.scrape("https://example.com", mode="full", dlq=DLQ())
result.dlq.items   # [{"url": ..., "mode": ..., "max_depth": ..., "max_pages": ...}, ...]

# Collect and save to file
result = rag.scrape("https://example.com", mode="full", dlq=DLQ("files/dlq/web.json"))
result.dlq.path    # "files/dlq/web.json" (None if no retryable failures)

# Retry
result = rag.scrape(dlq=result.dlq)          # from previous result
result = rag.scrape(dlq="files/dlq/web.json") # from file
```

When `result.dlq.path` is set, retrying with `rag.scrape(dlq=result.dlq)` writes any new failures back to the same file automatically.

```python
# Filter before retrying
result.dlq.items = [i for i in result.dlq.items if "docs" in i["url"]]
result = rag.scrape(dlq=result.dlq)
```

`url` and a retry `dlq` are mutually exclusive.

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `str \| list[str \| dict]` | — | URL(s) to scrape (mutually exclusive with retry `dlq`) |
| `mode` | `str` | `"each"` | `"each"` scrapes exact URLs; `"full"` crawls the entire site |
| `max_depth` | `int` | `3` | Max crawl depth (used with `mode="full"`) |
| `max_pages` | `int` | `200` | Max pages to scrape per URL |
| `verbose` | `bool` | `False` | Enable crawler logging |
| `frontmatter` | `bool` | `False` | Prepend YAML frontmatter to markdown outputs |
| `output_format` | `str` | `"markdown"` | `"markdown"` or `"json"` |
| `output_dest` | `str` | `"response"` | `"response"` or `"file"` |
| `output_dir` | `str` | `None` | Required when `output_dest="file"` |
| `dlq` | `DLQ \| str` | `None` | DLQ config (`DLQ()`, `DLQ("path")`) or retry input (`result.dlq`, `"path"`) |

## Result

```python
result.pages      # number of successfully scraped pages
result.failed     # number of failed pages
result.outputs    # list of output dicts
result.errors     # list of error dicts
result.dlq        # DLQ object (None if dlq param not set)
result.dlq.items  # list of retry input dicts
result.dlq.path   # path written to, or None
```
