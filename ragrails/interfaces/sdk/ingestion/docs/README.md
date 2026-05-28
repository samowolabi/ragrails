# Document Ingestion — `parse()`

Convert local files, file URLs, or raw bytes into markdown or JSON.

## Basic usage

```python
from ragrails import RagRails

rag = RagRails()

# Single file
result = rag.parse(files="report.pdf")

# Multiple files
result = rag.parse(files=["report.pdf", "guide.docx"])

# Entire folder
result = rag.parse(folder="docs/")
```

## Input types

```python
# Local file path
result = rag.parse(files="docs/report.pdf")

# Direct file URL
result = rag.parse(files="https://example.com/report.pdf")

# File bytes (e.g. server upload)
result = rag.parse(files={"content": pdf_bytes, "filename": "contract.pdf", "title": "Contract"})

# Mix of all types
result = rag.parse(files=[
    "docs/report.pdf",
    "https://example.com/guide.pdf",
    {"content": pdf_bytes, "filename": "contract.pdf"},
])
```

## Frontmatter

Add YAML frontmatter to markdown outputs with `frontmatter=True`. Ignored when `output_format="json"`.

```python
result = rag.parse(files="report.pdf", frontmatter=True)
print(result.outputs[0]["text"])
# ---
# title: "Report"
# source: "/path/to/report.pdf"
# id: "doc_abc123"
# ---
#
# # Report content...
```

## Output format

| `output_format` | Description |
|---|---|
| `"markdown"` | Parsed content as a markdown string (default) |
| `"json"` | Full structured output — text, title, source, metadata |

```python
# Markdown (default)
result = rag.parse(files="report.pdf")
result.outputs[0]["text"]   # markdown string

# JSON
result = rag.parse(files="report.pdf", output_format="json")
result.outputs[0]           # {"id", "title", "text", "source", "metadata", ...}
```

## Output destination

| `output_dest` | Description |
|---|---|
| `"response"` | Returns result in memory (default) |
| `"file"` | Saves to disk — requires `output_dir` |

```python
# Save as .md files
rag.parse(files="report.pdf", output_dest="file", output_dir="files/output/docs")

# Save as .json files
rag.parse(files="report.pdf", output_format="json", output_dest="file", output_dir="files/output/docs")

# Save with frontmatter
rag.parse(files="report.pdf", frontmatter=True, output_dest="file", output_dir="files/output/docs")

# Access saved path
result = rag.parse(files="report.pdf", output_dest="file", output_dir="files/output/docs")
result.outputs[0]["output_path"]   # "files/output/docs/report.md"
```

## Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `files` | `str \| list[str \| dict]` | — | File path(s), URL(s), or bytes dicts |
| `folder` | `str` | `None` | Path to a folder — all supported files are parsed |
| `frontmatter` | `bool` | `False` | Prepend YAML frontmatter to markdown outputs |
| `output_format` | `str` | `"markdown"` | `"markdown"` or `"json"` |
| `output_dest` | `str` | `"response"` | `"response"` or `"file"` |
| `output_dir` | `str` | `None` | Required when `output_dest="file"` |

## Result

```python
result.documents   # number of successfully parsed documents
result.failed      # number of failed documents
result.outputs     # list of output dicts
result.errors      # list of error dicts
```

## Supported file types

`.csv` `.docx` `.epub` `.html` `.htm` `.ipynb` `.json` `.md` `.msg` `.pdf` `.pptx` `.rss` `.tsv` `.txt` `.xls` `.xlsx` `.xml` `.zip`
