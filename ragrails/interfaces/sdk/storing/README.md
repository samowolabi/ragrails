# SDK Storing

Store embedded chunks in a vector database.

The SDK storing interface does not read files and does not create embeddings. It
accepts embedded chunks from `rag.embed(...)` and writes them to the configured
vector store.

## Basic Usage

```python
from ragrails import RagRails

rag = RagRails()

parsed = rag.parse(files=["docs/report.pdf"])
chunks = rag.chunk(markdown=parsed.outputs)
embedder = rag.embedder(provider="voyage", model="voyage-3")
embedded = rag.embed(chunks=chunks.items, embedder=embedder)

stored = rag.store(
    embedded_chunks=embedded.items,
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
)

print(stored.stored)
```

## API

```python
rag.store(
    embedded_chunks=embedded.items,
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
    batch_size=64,
    ensure_collection=True,
    options=None,
)
```

Edit stored chunks by exact chunk ID:

```python
result = rag.edit(
    chunks=[
        {
            "id": "chunk-id",
            "text": "Updated chunk text",
            "source": "docs/report.pdf",
            "metadata": {"title": "Report"},
        }
    ],
    embedder=embedder,
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
)
```

Delete stored chunks by exact chunk ID:

```python
result = rag.delete(
    ids=["chunk-id"],
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
)
```

## Result Shape

```python
StoreResult(
    inputs=10,
    stored=10,
    items=[
        {"id": "chunk-id", "source": "docs/report.pdf"},
    ],
    failed=0,
    provider="qdrant",
    collection="docs",
    errors=[],
)
```

`edit()` returns `EditResult`; `delete()` returns `DeleteResult`. Both include
requested count, success count, items, failed count, provider, collection, and
errors.
