# Retrieval

The public Ragrails retrieval SDK nomenclature is not finalized yet.

Retrieval uses the same vector-store registry as embedding. Set the provider
before running retrieval.

```bash
export VECTOR_DB_PROVIDER=qdrant
export VECTOR_DB_COLLECTION=rag_chunks

uv run python -m ragrails.pipeline.stg_04_retriever "How do payouts work?"
```

For Pinecone:

```bash
export PINECONE_API_KEY="..."
export VECTOR_DB_PROVIDER=pinecone
export VECTOR_DB_COLLECTION=rag-chunks

uv run python -m ragrails.pipeline.stg_04_retriever "How do payouts work?"
```

## Parameters

Retrieval is currently run through the stage command, not the public SDK.

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `query` | CLI argument | - | Yes | User question to search for. |
| `VECTOR_DB_PROVIDER` | Environment variable | `qdrant` | No | Vector database provider. Supports the same registry as storage. |
| `VECTOR_DB_COLLECTION` | Environment variable | provider default | No | Collection or index to search. |
| `PINECONE_API_KEY` | Environment variable | - | For Pinecone | Pinecone API key. |
| `VECTOR_DB_URL` | Environment variable | provider default | No | Vector database URL for local providers such as Qdrant or Weaviate. |

For now, start with ingestion:

```python
from ragrails import RagRails

result = RagRails().scrape(
    url="https://example.com",
    mode="full",
    output_dir="files/output/web_crawled",
)
```

Retrieval will be documented here after the public method name is chosen.
