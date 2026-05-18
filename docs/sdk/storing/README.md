# Storing

`store()` is the storage-oriented SDK method for persisting embedded chunk
vectors into the configured retrieval index.

It accepts the same parameters as `embed()` and returns `StoreResult`.

```python
from ragrails import RagRails

result = RagRails().store(
    input_dir="files/output/chunks/docs",
    vector_db="qdrant",
    collection="rag_chunks",
)

print(result.files)
print(result.chunks)
print(result.provider)
print(result.collection)
print(result.errors)
```

Storing is responsible for:

- ensuring the collection or index exists
- validating provider-specific collection names
- upserting by stable chunk ID
- preserving chunk payload metadata
- batching writes through the configured provider

See [Embedding](../embedding/README.md) for provider setup and shared
parameters.
