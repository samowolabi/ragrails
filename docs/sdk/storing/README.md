# Storing

`store()` persists embedded chunks in a vector database. `edit()` and `delete()`
manage already-stored chunks by exact chunk ID.

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
    collection="rag_chunks",
    url="http://localhost:6333",
)
```

Edit a stored chunk:

```python
edited = rag.edit(
    chunks=[
        {
            "id": "chunk-id",
            "text": "Updated text",
            "source": "docs/report.pdf",
            "metadata": {"title": "Report"},
        }
    ],
    embedder=embedder,
    vector_db="qdrant",
    collection="rag_chunks",
    url="http://localhost:6333",
)
```

Delete stored chunks:

```python
deleted = rag.delete(
    ids=["chunk-id"],
    vector_db="qdrant",
    collection="rag_chunks",
    url="http://localhost:6333",
)
```

Lifecycle operations are chunk-level only. Document-level delete and metadata
filter delete are not part of this stage yet.
