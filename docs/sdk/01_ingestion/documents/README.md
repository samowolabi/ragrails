# Document Ingestion

Use `RagRails().parse()` to convert local documents into markdown.

## Install

```bash
pip install ragrails
```

PDF files use `pymupdf4llm` first and fall back to `markitdown`. Other
supported document types use `markitdown`.

```python
from ragrails import RagRails

result = RagRails().parse(
    folder="files/input",
    output_dir="files/output/docs",
)

print(result.documents)
print(result.files)
print(result.errors)
```

## Ingest a Folder

Use `folder` to convert all supported files in a directory.

```python
from ragrails import RagRails

result = RagRails().parse(
    folder="files/input",
    output_dir="files/output/docs",
)
```

Ragrails currently discovers these extensions:

- `.csv`
- `.docx`
- `.epub`
- `.html`
- `.htm`
- `.ipynb`
- `.json`
- `.md`
- `.msg`
- `.pdf`
- `.pptx`
- `.rss`
- `.tsv`
- `.txt`
- `.xls`
- `.xlsx`
- `.xml`
- `.zip`

## Ingest Selected Files

Use `files` when you only want specific documents. File names are resolved
relative to `input_dir`.

```python
from ragrails import RagRails

result = RagRails().parse(
    files=["guide.pdf", "pricing.csv"],
    input_dir="files/input",
    output_dir="files/output/docs",
)
```

## Output

Document ingestion writes markdown files to `output_dir`.

```text
files/output/docs/
  guide.md
  pricing.md
```

## Custom Metadata

Pass dictionaries when you want explicit frontmatter metadata.

```python
from ragrails import RagRails

result = RagRails().parse(
    files=[
        {
            "filename": "guide.pdf",
            "title": "Product Guide",
            "description": "Internal product guide.",
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

## Frontmatter

Frontmatter is enabled by default.

```python
result = RagRails().parse(
    files=["guide.pdf"],
    frontmatter=True,
)
```

Disable it when you want only the converted markdown body.

```python
result = RagRails().parse(
    files=["guide.pdf"],
    frontmatter=False,
)
```

## Function

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

### `parse()` Parameters

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `files` | `str \| list[str \| dict] \| None` | `None` | Conditional | Specific files to parse. Use this when you do not pass `folder`. |
| `folder` | `str \| None` | `None` | Conditional | Folder containing supported documents. Use this when you do not pass `files`. |
| `input_dir` | `str` | `"files/input"` | No | Base folder used to resolve names in `files`. Ignored when `folder` is used. |
| `output_dir` | `str` | `"files/output/docs"` | No | Folder where markdown files are written. |
| `frontmatter` | `bool` | `True` | No | Adds document metadata to the top of each markdown file. |

## Result

`parse()` returns a `ParseResult`:

```python
print(result.documents)
print(result.failed)
print(result.output_dir)
print(result.files)
print(result.errors)
```

## Validation

`parse()` validates inputs before conversion starts.

It raises `ValueError` when:

- neither `files` nor `folder` is provided.
- both `files` and `folder` are provided.
- `folder` has no supported files.
- `input_dir` is empty when using `files`.
- `output_dir` is empty.
- selected file names are empty.
- selected file extensions are unsupported.

It raises `FileNotFoundError` when `folder` does not exist.

It raises `NotADirectoryError` when `folder` points to a file instead of a
directory.

```python
from ragrails import RagRails

RagRails().parse(
    files=["image.png"],
)
# ValueError: Unsupported document type '.png' for 'image.png'
```

## Error Handling

Per-file conversion failures are recorded in the returned result.

```python
result = RagRails().parse(
    folder="files/input",
)

if result.failed:
    print(result.errors)
```
