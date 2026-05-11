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
