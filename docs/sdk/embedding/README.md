# Embedding And Storing

`embed()` reads Ragrails chunk JSON files, creates embeddings, and persists
them in the configured retrieval index. `store()` remains available as a
storage-oriented alias for the same workflow.

Conceptually, this stage has two responsibilities:

- **Embedding**: choose the text to embed, batch chunks, call the embedder, and create vectors.
- **Storing**: ensure the collection or index exists, validate provider constraints, upsert by stable chunk ID, and preserve payload metadata.

## Install

Install one embedding and storing workflow extra:

```bash
pip install "ragrails[store-qdrant]"
pip install "ragrails[store-pinecone]"
pip install "ragrails[store-weaviate]"
```

Or install the embedding and vector DB providers separately:

```bash
pip install "ragrails[voyage,qdrant]"
pip install "ragrails[voyage,pinecone]"
pip install "ragrails[voyage,weaviate]"
```

Use it after ingestion and chunking:

```python
from ragrails import RagRails

rag = RagRails()

rag.scrape(
    url="https://example.com",
    mode="full",
    output_dir="files/output/web_crawled",
)

rag.chunk(
    input_dir="files/output/web_crawled",
    output_dir="files/output/chunks/web",
)

result = rag.embed(
    input_dir="files/output/chunks/web",
    vector_db="qdrant",
    collection="rag_chunks",
)

print(result.files)
print(result.chunks)
print(result.provider)
print(result.collection)
print(result.errors)
```

## Input

`embed()` reads every `.json` chunk file in the folder you pass:

```python
result = RagRails().embed(
    input_dir="files/output/chunks/docs",
    vector_db="qdrant",
    collection="rag_chunks",
)
```

You can embed chunks created from any ingestion source:

```python
RagRails().embed(input_dir="files/output/chunks/web")
RagRails().embed(input_dir="files/output/chunks/docs")
RagRails().embed(input_dir="files/output/chunks/api")
```

The folder must contain Ragrails chunk JSON files produced by `chunk()`.

## Embed Selected Files

Pass `files` when you only want to embed specific chunk files from the folder:

```python
result = RagRails().embed(
    input_dir="files/output/chunks/docs",
    files=["001_overview.json", "002_auth.json"],
    vector_db="qdrant",
    collection="rag_chunks",
)
```

## Embedding Model

`embed()` uses each chunk's `embed_text` when available and falls back to
`text`. The default embedder is Voyage:

```python
result = RagRails().embed(
    input_dir="files/output/chunks/docs",
    embedder="voyage",
    model="voyage-3",
)
```

Set the API key before running:

```bash
export VOYAGE_API_KEY="..."
```

## Qdrant

Qdrant is the simplest local development option.

Start Qdrant:

```bash
docker run -p 6333:6333 qdrant/qdrant
```

Embed chunks:

```python
result = RagRails().embed(
    input_dir="files/output/chunks/docs",
    vector_db="qdrant",
    url="http://localhost:6333",
    collection="rag_chunks",
)
```

## Pinecone

Pinecone is the managed vector DB option. Ragrails uses its own embedding model,
then stores the generated dense vectors in a Pinecone serverless index.

Set the API key:

```bash
export PINECONE_API_KEY="..."
```

Embed chunks:

```python
result = RagRails().embed(
    input_dir="files/output/chunks/docs",
    vector_db="pinecone",
    collection="rag-chunks",
)
```

Optional Pinecone settings:

```bash
export PINECONE_CLOUD=aws
export PINECONE_REGION=us-east-1
export PINECONE_NAMESPACE=
```

For Pinecone, `collection` maps to the Pinecone index name. Use lowercase
letters, digits, and hyphens only:

```text
rag-chunks
opencode-rag-chunks
budpay-rag-chunks
```

Do not use underscores for Pinecone index names:

```text
rag_chunks
opencode_rag_chunks
```

## Weaviate

Weaviate is supported for local and cloud vector storage. Ragrails uses its own
embedding model, then stores the generated dense vectors in a Weaviate
collection configured for self-provided vectors.

Run Weaviate locally with HTTP and gRPC exposed:

```bash
docker run -p 8080:8080 -p 50051:50051 cr.weaviate.io/semitechnologies/weaviate:1.36.9
```

Embed chunks:

```python
result = RagRails().embed(
    input_dir="files/output/chunks/docs",
    vector_db="weaviate",
    url="http://localhost:8080",
    collection="RagChunks",
)
```

For Weaviate Cloud:

```bash
export WEAVIATE_API_KEY="..."
```

```python
result = RagRails().embed(
    input_dir="files/output/chunks/docs",
    vector_db="weaviate",
    url="https://your-cluster.weaviate.cloud",
    collection="RagChunks",
)
```

Optional local connection settings:

```bash
export WEAVIATE_GRPC_HOST=localhost
export WEAVIATE_GRPC_PORT=50051
```

For Weaviate, `collection` maps to the Weaviate collection name. Use a name that
starts with an uppercase letter:

```text
RagChunks
OpenCodeChunks
BudPayChunks
```

## Function

```python
RagRails().embed(
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

### `embed()` Parameters

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `input_dir` | `str` | `"files/output/chunks"` | No | Folder containing Ragrails chunk JSON files. |
| `vector_db` | `"qdrant" \| "pinecone" \| "weaviate"` | `"qdrant"` | No | Vector database provider to write to. |
| `collection` | `str \| None` | `None` | No | Collection, index, or class name, depending on provider. Provider defaults may apply when omitted. |
| `url` | `str \| None` | `None` | No | Vector database URL. Useful for local Qdrant or Weaviate. |
| `files` | `str \| list[str] \| None` | `None` | No | Embed only selected chunk JSON files from `input_dir`. |
| `batch_size` | `int` | `64` | No | Number of chunks embedded and stored per batch. |
| `embedder` | `str` | `"voyage"` | No | Embedding provider. Currently Voyage is the documented SDK path. |
| `model` | `str` | `"voyage-3"` | No | Embedding model name passed to the embedder. |

## Result

```python
EmbedResult(
    files=int,
    chunks=int,
    input_dir=str,
    provider=str,
    collection=str,
    errors=list[str],
)
```

## Stage Runner

The lower-level stage runner still works:

```bash
uv run python -m ragrails.pipeline.stg_03_embedder --input-dir files/output/chunks/docs
```

Embed one file from a folder:

```bash
uv run python -m ragrails.pipeline.stg_03_embedder file 001_overview.json --input-dir files/output/chunks/docs
```

## What Gets Stored

Each vector point contains:

```python
{
    "id": "stable-chunk-id",
    "vector": [0.012, -0.034, ...],
    "payload": {
        "text": "chunk text",
        "source_url": "https://example.com/page",
        "title": "Page title",
        "content_hash": "...",
        "...": "other chunk metadata"
    }
}
```

The retriever expects `payload["text"]` to be present, so custom vector store
adapters must preserve that payload field.

Storing is idempotent because chunk IDs are stable. Re-running embedding for the
same chunk updates the existing vector point instead of creating duplicates.

## Failure Cases

General setup issues:

- Missing `VOYAGE_API_KEY`
- The input folder does not contain chunk JSON files

### Qdrant

- Qdrant is not running.
- `url` or `VECTOR_DB_URL` points to the wrong host or port.
- `collection` is different from the collection used during retrieval.
- Docker is running, but port `6333` is not exposed.

### Pinecone

- `PINECONE_API_KEY` is missing or invalid.
- `collection` contains underscores. Use hyphens, for example `rag-chunks`.
- `collection` is longer than Pinecone's index-name limit.
- `PINECONE_CLOUD` or `PINECONE_REGION` points to a region you do not use.
- The Pinecone account does not have permission or quota to create a serverless index.

### Weaviate

- Weaviate is not running.
- Local Weaviate is missing the gRPC port. Expose both `8080` and `50051`.
- `url` or `VECTOR_DB_URL` points to the wrong HTTP endpoint.
- `WEAVIATE_API_KEY` is missing or invalid for Weaviate Cloud.
- `collection` does not start with an uppercase letter, for example `RagChunks`.
- `collection` contains unsupported characters. Use only letters and digits.

## Next Step

After embedding vectors, run retrieval:

```python
from ragrails import RagRails

result = RagRails().retrieve(
    "your query",
    vector_db="qdrant",
    collection="rag_chunks",
)
```
