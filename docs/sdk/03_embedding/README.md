# Store

`store()` embeds Ragrails chunk JSON files and writes the vectors to a vector
database.

## Install

Install one store workflow extra:

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

result = rag.store(
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

`store()` reads every `.json` chunk file in the folder you pass:

```python
result = RagRails().store(
    input_dir="files/output/chunks/docs",
    vector_db="qdrant",
    collection="rag_chunks",
)
```

You can store chunks created from any ingestion source:

```python
RagRails().store(input_dir="files/output/chunks/web")
RagRails().store(input_dir="files/output/chunks/docs")
RagRails().store(input_dir="files/output/chunks/api")
```

The folder must contain Ragrails chunk JSON files produced by `chunk()`.

## Store Selected Files

Pass `files` when you only want to store specific chunk files from the folder:

```python
result = RagRails().store(
    input_dir="files/output/chunks/docs",
    files=["001_overview.json", "002_auth.json"],
    vector_db="qdrant",
    collection="rag_chunks",
)
```

## Embedding Model

`store()` embeds the chunk text before writing to the vector DB. The default
embedder is Voyage:

```python
result = RagRails().store(
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

Store chunks:

```python
result = RagRails().store(
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

Store chunks:

```python
result = RagRails().store(
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

Store chunks:

```python
result = RagRails().store(
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
result = RagRails().store(
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

## Result

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

After storing vectors, run retrieval:

```bash
uv run python -m ragrails.pipeline.stg_04_retriever "your query"
```
