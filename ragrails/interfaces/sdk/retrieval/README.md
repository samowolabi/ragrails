# SDK Retrieval

Retrieve relevant chunks from a vector database.

Configured clients create the query embedder and vector store automatically.

## Basic Usage

```python
from ragrails import RagRails

rag = RagRails(
    collection="docs",
    vector_store={"provider": "qdrant", "url": "http://localhost:6333"},
    embedding={"provider": "voyage", "model": "voyage-3"},
    llm={"provider": "openai", "model": "gpt-5.5"},
    reranker={"enabled": True, "provider": "voyage", "model": "rerank-2-lite"},
)

result = rag.retrieve(
    "How do I authenticate?",
    top_k=10,
)

for item in result.items:
    print(item.chunk_id, item.score, item.text)
```

## With Reranking

```python
result = rag.retrieve(
    "How do I authenticate?",
    use_rerank=True,
    top_k=20,
    rerank_top_k=5,
)
```

## With Query Rewrite

```python
result = rag.retrieve(
    "How do I do it?",
    use_query_rewrite=True,
    rewrite_context="Product documentation",
    session_context="User is asking about authentication",
)
```

## Result Shape

```python
RetrieveResult(
    query="How do I authenticate?",
    search_query="How do I authenticate?",
    retrieved=5,
    items=[...],
    failed=0,
    errors=[],
)
```

Each retrieved item includes `chunk_id`, which is the identifier to pass to
edit and delete operations. It is read from stored chunk metadata when present
and falls back to the vector point id.
