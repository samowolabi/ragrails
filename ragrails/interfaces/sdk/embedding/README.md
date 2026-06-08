# SDK Embedding

Embed chunk dictionaries in memory.

The SDK embedding interface does not read chunk files and does not write to a vector database. Storage is a separate step.

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

embedded = rag.embed(
    chunks=chunks.items,
    batch_size=64,
)

print(embedded.embedded)
print(embedded.items[0]["embedding"])
```

## Result Shape

```python
EmbedResult(
    inputs=1,
    embedded=1,
    items=[
        {
            "id": "chunk-id",
            "source": "docs/report.pdf",
            "text": "Visible chunk text",
            "embed_text": "Text sent to the embedding model",
            "embedding": [0.01, 0.02],
            "metadata": {},
        }
    ],
    failed=0,
    errors=[],
)
```

## Store After Embedding

```python
stored = rag.store(
    embedded_chunks=embedded.items,
)
```
