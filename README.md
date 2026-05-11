# Ragrails

[![PyPI](https://img.shields.io/pypi/v/ragrails)](https://pypi.org/project/ragrails/)
[![Python](https://img.shields.io/pypi/pyversions/ragrails)](https://pypi.org/project/ragrails/)
[![Downloads](https://static.pepy.tech/badge/ragrails)](https://pepy.tech/project/ragrails)
[![License](https://img.shields.io/pypi/l/ragrails)](LICENSE)

Ragrails is a modular RAG SDK for ingesting web pages, local documents, and REST
API responses, converting them into clean markdown, chunking them for retrieval,
and storing embeddings in pluggable vector databases.

It is built for retrieval-augmented generation workflows that need source
ingestion, markdown normalization, chunking, semantic search, vector storage,
and evaluation as separate stages.

The public SDK starts with one class:

```python
from ragrails import RagRails

rag = RagRails()
```

## Current SDK

The ingestion, chunking, and vector storage SDK surfaces are available now.

```python
rag.scrape(...)  # web pages and websites
rag.parse(...)   # local files and folders
rag.fetch(...)   # REST API responses
rag.chunk(...)   # markdown files to RAG chunks
rag.store(...)   # chunk JSON files to a vector DB
```

Detailed SDK docs:

1. [Ingestion](docs/sdk/01_ingestion/README.md)
   - [URL ingestion](docs/sdk/01_ingestion/url/README.md)
   - [Document ingestion](docs/sdk/01_ingestion/documents/README.md)
   - [API ingestion](docs/sdk/01_ingestion/api/README.md)
2. [Chunking](docs/sdk/02_chunking/README.md)
3. [Embedding](docs/sdk/03_embedding/README.md)
4. [Retrieval](docs/sdk/04_retrieval/README.md)

## Installation

Install the lightweight SDK:

```bash
pip install ragrails
```

This is enough to import the SDK:

```python
from ragrails import RagRails
```

Install extras for the stage or provider you need.

| Stage | Install |
|---|---|
| URL ingestion | `pip install "ragrails[url]"` |
| Document ingestion | `pip install "ragrails[docs]"` |
| API ingestion | `pip install "ragrails[api]"` |
| Chunking | `pip install "ragrails[chunk]"` |
| Store in Qdrant | `pip install "ragrails[store-qdrant]"` |
| Store in Pinecone | `pip install "ragrails[store-pinecone]"` |
| Store in Weaviate | `pip install "ragrails[store-weaviate]"` |

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
| Everything | `pip install "ragrails[all]"` |

Common workflow installs:

| Workflow | Install |
|---|---|
| Scrape URLs, chunk, store in Qdrant | `pip install "ragrails[url,chunk,voyage,qdrant]"` |
| Parse documents, chunk, store in Pinecone | `pip install "ragrails[docs,chunk,voyage,pinecone]"` |
| Fetch APIs, chunk, store in Weaviate | `pip install "ragrails[api,chunk,voyage,weaviate]"` |
| Qdrant storage shortcut | `pip install "ragrails[store-qdrant]"` |
| Pinecone storage shortcut | `pip install "ragrails[store-pinecone]"` |
| Weaviate storage shortcut | `pip install "ragrails[store-weaviate]"` |

`crawl4ai` pulls in Playwright as a package dependency for URL ingestion. You may
still need to install browser binaries:

```bash
playwright install
```

## Requirements

Later RAG stages use provider API keys:

```bash
export VOYAGE_API_KEY="..."
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

Embedding and retrieval also need a vector database. Ragrails currently ships
with Qdrant, Pinecone, and Weaviate adapters behind the same vector store
interface.

## Vector DB Providers

Choose a vector DB provider before storing, retrieving, chatting, or running
evals.

Provider names:

```text
qdrant
pinecone
weaviate
```

### Qdrant

Qdrant is the easiest local option while developing.

```bash
docker run -p 6333:6333 qdrant/qdrant
```

```bash
export VECTOR_DB_PROVIDER=qdrant
export VECTOR_DB_URL=http://localhost:6333
export VECTOR_DB_COLLECTION=rag_chunks
```

### Pinecone

Pinecone is the managed vector DB option. Ragrails uses its existing embedding
model and stores dense vectors in a Pinecone serverless index.

```bash
export PINECONE_API_KEY="..."
export VECTOR_DB_PROVIDER=pinecone
export VECTOR_DB_COLLECTION=rag-chunks
```

Optional Pinecone settings:

```bash
export PINECONE_CLOUD=aws
export PINECONE_REGION=us-east-1
export PINECONE_NAMESPACE=
```

For Pinecone, `VECTOR_DB_COLLECTION` maps to the Pinecone index name. Use
lowercase letters, digits, and hyphens only, for example `rag-chunks`.

### Weaviate

Weaviate is another managed or self-hosted vector DB option. Ragrails uses its
own embedding model and stores dense vectors in a Weaviate collection configured
for self-provided vectors.

For local Weaviate, expose both HTTP and gRPC ports:

```bash
docker run -p 8080:8080 -p 50051:50051 cr.weaviate.io/semitechnologies/weaviate:1.36.9
```

```bash
export VECTOR_DB_PROVIDER=weaviate
export VECTOR_DB_URL=http://localhost:8080
export VECTOR_DB_COLLECTION=RagChunks
```

For Weaviate Cloud:

```bash
export WEAVIATE_API_KEY="..."
export VECTOR_DB_PROVIDER=weaviate
export VECTOR_DB_URL="https://your-cluster.weaviate.cloud"
export VECTOR_DB_COLLECTION=RagChunks
```

For Weaviate, `VECTOR_DB_COLLECTION` maps to the collection name. Use a name
that starts with an uppercase letter, for example `RagChunks`.

After choosing a provider, store chunks with the SDK:

```python
from ragrails import RagRails

result = RagRails().store(
    input_dir="files/output/chunks",
    vector_db="qdrant",
    collection="rag_chunks",
)

print(result.files)
print(result.chunks)
print(result.provider)
print(result.collection)
```

The lower-level stage runner also reads the same environment variables:

```bash
uv run python -m ragrails.pipeline.stg_03_embedder
uv run python -m ragrails.pipeline.stg_04_retriever "your query"
```

## URL Ingestion

Scrape one exact page:

```python
from ragrails import RagRails

result = RagRails().scrape(
    url="https://example.com/about",
    mode="each",
    output_dir="files/output/web_crawled",
)

print(result.pages)
print(result.files)
print(result.errors)
```

Crawl a website:

```python
result = RagRails().scrape(
    url="https://example.com",
    mode="full",
    output_dir="files/output/web_crawled",
    max_depth=3,
    max_pages=200,
)
```

## Document Ingestion

Parse a folder of local documents into markdown:

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

Parse selected files with custom metadata:

```python
result = RagRails().parse(
    files=[
        {
            "filename": "guide.pdf",
            "title": "Product Guide",
            "description": "Internal product guide.",
        }
    ],
    input_dir="files/input",
    output_dir="files/output/docs",
)
```

Supported discovery extensions for folders:

```text
.csv, .docx, .epub, .html, .htm, .ipynb, .json, .md, .msg,
.pdf, .pptx, .rss, .tsv, .txt, .xls, .xlsx, .xml, .zip
```

## API Ingestion

Fetch a REST API response into markdown:

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
print(result.errors)
```

Pass request options when needed:

```python
result = RagRails().fetch(
    url="https://api.example.com/v1/search",
    method="POST",
    headers={"Authorization": "Bearer <token>"},
    body={"query": "payments"},
    title="Search Results",
)
```

## Chunking

Split markdown files into RAG-ready JSON chunks:

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

Chunk markdown created by any ingestion method:

```python
result = RagRails().chunk(
    input_dir="files/output/docs",
    output_dir="files/output/chunks/docs",
    chunk_size=1200,
    chunk_overlap=150,
)
```

Preview one markdown file in memory:

```python
chunks = RagRails().chunk_file(
    "files/output/docs/guide.md",
)

print(len(chunks))
print(chunks[0]["metadata"])
```

## Store

Embed every chunk JSON file in a folder and store the vectors:

```python
from ragrails import RagRails

result = RagRails().store(
    input_dir="files/output/chunks/docs",
    vector_db="qdrant",
    collection="rag_chunks",
)

print(result.files)
print(result.chunks)
print(result.errors)
```

Store in Pinecone:

```python
result = RagRails().store(
    input_dir="files/output/chunks/docs",
    vector_db="pinecone",
    collection="rag-chunks",
)
```

Store in Weaviate:

```python
result = RagRails().store(
    input_dir="files/output/chunks/docs",
    vector_db="weaviate",
    url="http://localhost:8080",
    collection="RagChunks",
)
```

Store selected chunk files from a folder:

```python
result = RagRails().store(
    input_dir="files/output/chunks/docs",
    files=["001_overview.json", "002_auth.json"],
    vector_db="qdrant",
    collection="rag_chunks",
)
```

Provider-specific failures to check first:

```text
qdrant    Qdrant is not running, or port 6333 is not exposed.
pinecone  PINECONE_API_KEY is missing, or the index name uses underscores.
weaviate  Weaviate is not running, gRPC 50051 is not exposed, or the collection name is invalid.
```

## Output

Ragrails writes markdown files to the output directory you choose:

```text
files/output/web_crawled/
files/output/docs/
files/output/api/
files/output/chunks/
```

By default, files include Ragrails frontmatter metadata. Disable it with
`frontmatter=False` when you only want the markdown body.

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

## API Reference

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

```python
RagRails().chunk_file(
    path,
    *,
    chunk_size=2000,
    chunk_overlap=200,
    min_chunk_length=100,
)
```

```python
RagRails().store(
    *,
    input_dir="files/output/chunks",
    vector_db="qdrant",
    collection=None,
    url=None,
    files=None,
    batch_size=64,
    embedder="voyage",
    model="voyage-3",
)
```

Supported `vector_db` values:

```text
qdrant
pinecone
weaviate
```

## Status

Ingestion, chunking, and vector storage are available through the public SDK.
Retrieval, chat, and eval already exist internally and will be exposed next.
