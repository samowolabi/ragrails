# Retrieval

`retrieve()` searches a vector database for chunks relevant to a query.

Create the query embedder as its own object, then pass it into `retrieve()`.
This keeps retrieval provider-agnostic and makes custom embedders work the same
way as built-in providers.

## Install

Install the matching vector database and embedding extras:

```bash
pip install "ragrails[voyage,qdrant]"
pip install "ragrails[voyage,pinecone]"
pip install "ragrails[voyage,weaviate]"
```

For reranking, install:

```bash
pip install "ragrails[rerank]"
```

Set provider credentials when needed:

```bash
export VOYAGE_API_KEY="..."
export PINECONE_API_KEY="..."
export WEAVIATE_API_KEY="..."
```

## Basic Usage

```python
from ragrails import RagRails

rag = RagRails()
query_embedder = rag.embedder(provider="voyage", model="voyage-3", input_type="query")

result = rag.retrieve(
    "How do payouts work?",
    embedder=query_embedder,
    vector_db="qdrant",
    collection="rag_chunks",
    top_k=10,
)

for item in result.items:
    print(item.score, item.metadata.get("title"), item.text[:200])
```

## Reranking

Use reranking to rescore the retrieved candidates with a cross-encoder:

```python
rag = RagRails()
query_embedder = rag.embedder(provider="voyage", model="voyage-3", input_type="query")
reranker = rag.reranker(provider="voyage", model="rerank-2-lite")

result = rag.retrieve(
    "How do payouts work?",
    embedder=query_embedder,
    vector_db="qdrant",
    collection="rag_chunks",
    top_k=20,
    use_rerank=True,
    reranker=reranker,
    rerank_top_k=5,
)
```

## Function

```python
RagRails().retrieve(
    query,
    *,
    embedder,
    vector_db="qdrant",
    collection=None,
    url=None,
    options=None,
    top_k=10,
    use_query_rewrite=False,
    rewrite_llm=None,
    rewrite_context="",
    session_context="",
    use_rerank=False,
    reranker=None,
    rerank_top_k=5,
)
```

### `retrieve()` Parameters

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `query` | `str` | - | Yes | Query text to search for. |
| `embedder` | embedding model object | - | Yes | Query embedder object, usually from `rag.embedder(..., input_type="query")`. |
| `vector_db` | `"qdrant" \| "pinecone" \| "weaviate"` | `"qdrant"` | No | Vector database provider to search. |
| `collection` | `str \| None` | `None` | No | Collection, index, or class name. Provider defaults apply when omitted. |
| `url` | `str \| None` | `None` | No | Vector database URL. Useful for local Qdrant or Weaviate. |
| `options` | `dict \| None` | `None` | No | Extra options forwarded to the vector store provider. |
| `top_k` | `int` | `10` | No | Number of vector search candidates to return. |
| `use_query_rewrite` | `bool` | `False` | No | Rewrite the query with an LLM before vector search. |
| `rewrite_llm` | LLM object | `None` | Required when query rewrite is enabled | LLM object used for query rewrite. |
| `rewrite_context` | `str` | `""` | No | Domain context passed to query rewrite. |
| `session_context` | `str` | `""` | No | Conversation context passed to query rewrite. |
| `use_rerank` | `bool` | `False` | No | Rerank retrieved candidates. |
| `reranker` | reranker object | `None` | Required when rerank is enabled | Reranker object, usually from `rag.reranker(...)`. |
| `rerank_top_k` | `int` | `5` | No | Number of reranked results to return. |

## Result

```python
RetrieveResult(
    query=str,
    search_query=str,
    retrieved=int,
    items=[
        RetrievedChunk(
            id=str,
            score=float,
            text=str,
            metadata=dict,
            rerank_score=float | None,
        )
    ],
    failed=int,
    errors=list[dict],
)
```

## Stage Runner

The lower-level stage runner still works:

```bash
uv run python -m ragrails.core.stg_05_retriever "How do payouts work?"
```
