# API Ingestion — `fetch()`

Fetch paginated REST API endpoints and return each response page as a markdown or JSON document.

## Basic usage

```python
from ragrails import RagRails

rag = RagRails()

# Single endpoint
result = rag.fetch("https://api.example.com/posts")

# With options
result = rag.fetch(
    "https://api.example.com/posts",
    method="GET",
    headers={"Authorization": "Bearer token"},
    params={"limit": 100},
    pagination={"type": "page", "param": "page"},
    max_pages=10,
    timeout=30.0,
)
```

## Batch endpoints

```python
result = rag.fetch(apis=[
    "https://api.example.com/posts",
    {
        "url": "https://api.example.com/users",
        "title": "Users",
        "headers": {"Authorization": "Bearer token"},
        "max_pages": 5,
    },
])
```

## Frontmatter

Add YAML frontmatter to markdown outputs with `frontmatter=True`. Ignored when `output_format="json"`.

```python
result = rag.fetch("https://api.example.com/posts", frontmatter=True)
print(result.outputs[0]["text"])
# ---
# title: "Posts — page 1"
# source: "https://api.example.com/posts"
# id: "api_abc123"
# ---
#
# # Posts — page 1...
```

## Output format

| `output_format` | Description |
|---|---|
| `"markdown"` | Response pages as markdown text (default) |
| `"json"` | Full structured output — text, title, source, metadata |

```python
# Markdown (default)
result = rag.fetch("https://api.example.com/posts")
result.outputs[0]["text"]   # markdown string

# JSON
result = rag.fetch("https://api.example.com/posts", output_format="json")
result.outputs[0]           # {"id", "title", "text", "source", "metadata", ...}
```

## Output destination

| `output_dest` | Description |
|---|---|
| `"response"` | Returns result in memory (default) |
| `"file"` | Saves to disk — requires `output_dir` |

```python
# Save as .md files
rag.fetch("https://api.example.com/posts", output_dest="file", output_dir="files/output/api")

# Save as .json files
rag.fetch("https://api.example.com/posts", output_format="json", output_dest="file", output_dir="files/output/api")

# Save with frontmatter
rag.fetch("https://api.example.com/posts", frontmatter=True, output_dest="file", output_dir="files/output/api")

# Access saved path
result = rag.fetch("https://api.example.com/posts", output_dest="file", output_dir="files/output/api")
result.outputs[0]["output_path"]   # "files/output/api/001_api_example_com_posts.md"
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `str` | — | Single endpoint URL |
| `apis` | `list[str \| dict]` | — | Batch of endpoints (use instead of `url`) |
| `title` | `str` | auto | Title for the response document |
| `description` | `str` | `""` | Description added to document metadata |
| `method` | `str` | `"GET"` | HTTP method |
| `headers` | `dict` | `None` | Request headers |
| `params` | `dict` | `None` | Query parameters |
| `body` | `dict` | `None` | Request body |
| `pagination` | `dict` | `None` | Pagination config |
| `max_pages` | `int` | `100` | Maximum pages to fetch |
| `timeout` | `float` | `None` | Request timeout in seconds |
| `frontmatter` | `bool` | `False` | Prepend YAML frontmatter to markdown outputs |
| `output_format` | `str` | `"markdown"` | `"markdown"` or `"json"` |
| `output_dest` | `str` | `"response"` | `"response"` or `"file"` |
| `output_dir` | `str` | `None` | Required when `output_dest="file"` |

## Result

```python
result.documents   # number of successfully fetched pages
result.failed      # number of failed pages
result.outputs     # list of output dicts
result.errors      # list of error dicts
```
