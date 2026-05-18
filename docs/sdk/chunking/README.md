# Chunking

Use `RagRails().chunk()` to split markdown files into RAG-ready JSON chunks.

## Contract

Chunking reads markdown files produced by ingestion and writes structured JSON
chunk files for embedding.

Chunking is responsible for:

- parsing frontmatter metadata
- preserving source path, title, description, and original type
- splitting content into retrieval-sized chunks
- preserving heading context
- keeping code blocks atomic where possible
- splitting large tables while retaining header context
- repairing links that cross chunk boundaries
- dropping navigation-heavy chunks
- assigning stable chunk IDs and content hashes

## Install

```bash
pip install "ragrails[chunk]"
```

```python
from ragrails import RagRails

result = RagRails().chunk(
    input_dir="files/output/web_crawled",
    output_dir="files/output/chunks",
)

print(result.files)
print(result.chunks)
print(result.output_files)
print(result.errors)
```

## Input

`chunk()` expects a directory containing markdown files.

```text
files/output/web_crawled/
  001_index.md
  002_about.md
  003_pricing.md
```

The markdown can come from any Ragrails ingestion method:

```python
rag.scrape(...)
rag.parse(...)
rag.fetch(...)
```

## Example: Chunk Scraped Pages

```python
from ragrails import RagRails

rag = RagRails()

rag.scrape(
    url="https://example.com",
    mode="full",
    output_dir="files/output/web_crawled",
)

result = rag.chunk(
    input_dir="files/output/web_crawled",
    output_dir="files/output/chunks/web",
)

print(result.chunks)
print(result.output_files)
```

## Example: Chunk Parsed Documents

```python
from ragrails import RagRails

rag = RagRails()

rag.parse(
    folder="files/input",
    output_dir="files/output/docs",
)

result = rag.chunk(
    input_dir="files/output/docs",
    output_dir="files/output/chunks/docs",
)
```

## Example: Chunk API Responses

```python
from ragrails import RagRails

rag = RagRails()

rag.fetch(
    url="https://api.example.com/v1/products",
    title="Products",
    output_dir="files/output/api",
)

result = rag.chunk(
    input_dir="files/output/api",
    output_dir="files/output/chunks/api",
)
```

## Example: Custom Chunk Settings

```python
from ragrails import RagRails

result = RagRails().chunk(
    input_dir="files/output/web_crawled",
    output_dir="files/output/chunks",
    chunk_size=1200,
    chunk_overlap=150,
    min_chunk_length=80,
)
```

Use smaller chunks when you want tighter retrieval granularity. Use larger
chunks when preserving more local context matters.

## Output

Each input markdown file becomes a JSON chunk file.

```text
files/output/chunks/
  001_index.json
  002_about.json
  003_pricing.json
```

Each chunk includes:

- `text`
- `embed_text`
- `metadata.id`
- `metadata.chunk_id`
- `metadata.content_hash`
- `metadata.heading`
- `metadata.path`
- `metadata.title`

Table chunks may also include:

- `metadata.table_id`
- `metadata.columns`
- `metadata.row_start`
- `metadata.row_end`

## Chunk One File

Use `chunk_file()` when you want chunks returned in memory.

```python
from ragrails import RagRails

chunks = RagRails().chunk_file(
    "files/output/web_crawled/001_index.md",
)

print(len(chunks))
print(chunks[0]["metadata"])
print(chunks[0]["text"])
```

Preview the first few chunks:

```python
for chunk in chunks[:3]:
    print(chunk["metadata"]["chunk_id"])
    print(chunk["text"][:300])
```

## Function

```python
RagRails().chunk(
    *,
    input_dir="files/output/web_crawled",
    output_dir="files/output/chunks",
    chunk_size=2000,
    chunk_overlap=200,
    min_chunk_length=100,
)
```

### `chunk()` Parameters

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `input_dir` | `str` | `"files/output/web_crawled"` | No | Folder containing markdown files to chunk. |
| `output_dir` | `str` | `"files/output/chunks"` | No | Folder where chunk JSON files are written. |
| `chunk_size` | `int` | `2000` | No | Target maximum chunk size in characters. |
| `chunk_overlap` | `int` | `200` | No | Character overlap between neighboring chunks. |
| `min_chunk_length` | `int` | `100` | No | Minimum chunk length to keep. Shorter chunks are dropped. |

```python
RagRails().chunk_file(
    path,
    *,
    chunk_size=2000,
    chunk_overlap=200,
    min_chunk_length=100,
)
```

### `chunk_file()` Parameters

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `path` | `str` | - | Yes | Path to one markdown file to chunk in memory. |
| `chunk_size` | `int` | `2000` | No | Target maximum chunk size in characters. |
| `chunk_overlap` | `int` | `200` | No | Character overlap between neighboring chunks. |
| `min_chunk_length` | `int` | `100` | No | Minimum chunk length to keep. Shorter chunks are dropped. |

## Result

`chunk()` returns a `ChunkResult`:

```python
print(result.files)
print(result.chunks)
print(result.output_dir)
print(result.output_files)
print(result.failed)
print(result.errors)
```

`chunk_file()` returns a list of chunk dictionaries.

## Validation

`chunk()` validates inputs before chunking starts.

It raises an error when:

- `input_dir` is empty.
- `output_dir` is empty.
- `input_dir` does not exist.
- `input_dir` is not a directory.
- `input_dir` contains no markdown files.
- `chunk_size` is less than `1`.
- `chunk_overlap` is negative.
- `chunk_overlap` is greater than or equal to `chunk_size`.
- `min_chunk_length` is less than `1`.

`chunk_file()` also validates that `path` exists, is a file, and has a `.md`
extension.
