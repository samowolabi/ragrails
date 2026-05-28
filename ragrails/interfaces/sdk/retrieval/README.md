# SDK Retrieval

Retrieve relevant chunks from a vector database.

The SDK retrieval interface accepts an embedder object. It does not create the
embedder inside `retrieve()`, so custom embedders and provider objects work the
same way.

## Basic Usage

```python
from ragrails import RagRails

rag = RagRails()

query_embedder = rag.embedder(
    provider="voyage",
    model="voyage-3",
    input_type="query",
)

result = rag.retrieve(
    "How do I authenticate?",
    embedder=query_embedder,
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
    top_k=10,
)

for item in result.items:
    print(item.score, item.text)
```

## With Reranking

```python
query_embedder = rag.embedder(provider="voyage", model="voyage-3", input_type="query")
reranker = rag.reranker(provider="voyage", model="rerank-2-lite")

result = rag.retrieve(
    "How do I authenticate?",
    embedder=query_embedder,
    vector_db="qdrant",
    collection="docs",
    use_rerank=True,
    reranker=reranker,
    top_k=20,
    rerank_top_k=5,
)
```

## With Query Rewrite

```python
result = rag.retrieve(
    "How do I do it?",
    embedder=query_embedder,
    vector_db="qdrant",
    collection="docs",
    use_query_rewrite=True,
    rewrite_llm=llm,
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
