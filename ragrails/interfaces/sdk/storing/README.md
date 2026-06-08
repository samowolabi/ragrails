# SDK Storing

Store embedded chunks in a vector database.

The SDK storing interface writes embedded chunks to the configured vector store.
Configured clients do not need repeated `vector_db`, `collection`, and `url`
arguments.

## Basic Usage

```python
from ragrails import RagRails

rag = RagRails(
    collection="docs",
    vector_store={"provider": "qdrant", "url": "http://localhost:6333"},
    embedding={"provider": "voyage", "model": "voyage-3"},
)

parsed = rag.parse(files=["docs/report.pdf"])
chunks = rag.chunk(markdown=parsed.outputs)
embedded = rag.embed(chunks=chunks.items)

stored = rag.store(
    embedded_chunks=embedded.items,
)

print(stored.stored)
```

For Qdrant Cloud:

```python
rag = RagRails(
    collection="docs",
    vector_store={"provider": "qdrant_cloud", "url": "https://cluster.example.qdrant.io"},
    embedding={"provider": "voyage", "model": "voyage-3"},
)
```

Set `QDRANT_API_KEY` before running cloud-backed commands.

## API

```python
rag.store(
    embedded_chunks=embedded.items,
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
)
```

Delete stored chunks by exact chunk ID:

```python
result = rag.delete(
    ids=["chunk-id"],
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
