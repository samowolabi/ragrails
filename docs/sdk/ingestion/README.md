# SDK Ingestion

SDK ingestion turns URLs, documents, and REST API responses into structured
markdown outputs.

By default, ingestion returns data in memory. It does not write files and does
not add frontmatter unless you explicitly ask for those SDK conveniences.

## Methods

| Source | Method | Details |
|---|---|---|
| URLs | `rag.scrape(...)` | [URL ingestion](url/README.md) |
| Documents | `rag.parse(...)` | [Document ingestion](documents/README.md) |
| REST APIs | `rag.fetch(...)` | [API ingestion](api/README.md) |

## Output Contract

Every ingestion method returns a result object with:

```python
result.outputs  # list of output dictionaries
result.errors   # list of structured error dictionaries
result.failed   # failed item count
```

Each output contains:

```python
{
    "id": "...",
    "display_id": "...",
    "source": "...",
    "title": "...",
    "text": "# Markdown content",
    "metadata": {...},
}
```

## Optional File Output

File writing is opt-in:

```python
result = rag.parse(
    files="docs/report.pdf",
    output_dest="file",
    output_dir="files/output/docs",
)

print(result.outputs[0]["output_path"])
```

Use this only when you want the SDK to persist outputs for you. Core ingestion
still returns in-memory data; file output belongs to the SDK interface.

## Optional Frontmatter

Frontmatter is also opt-in and only affects markdown output:

```python
result = rag.scrape(
    "https://example.com/docs",
    frontmatter=True,
)
```

When `output_format="json"`, frontmatter is ignored because metadata is already
available as structured fields.

## Install

Document and API ingestion are included in the base install:

```bash
pip install ragrails
```

URL ingestion uses browser-backed crawling and needs the URL extra:

```bash
pip install "ragrails[url]"
```

Then install the Playwright browser once in the same Python environment:

```python
from ragrails import RagRails

RagRails().setup_url()
```
