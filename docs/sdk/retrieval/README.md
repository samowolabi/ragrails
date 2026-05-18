# Retrieval

`retrieve()` searches a vector database for chunks relevant to a query.

Retrieval uses the same vector-store registry and embedding provider as
embedding and storage. The query embedder runs with `input_type="query"` so the
query vector is optimized for search.

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

result = RagRails().retrieve(
    "How do payouts work?",
    vector_db="qdrant",
    collection="rag_chunks",
    top_k=10,
)

for item in result.results:
    print(item.score, item.metadata.get("title"), item.text[:200])
```

## Reranking

Use reranking to rescore the retrieved candidates with a cross-encoder:

```python
result = RagRails().retrieve(
    "How do payouts work?",
    vector_db="qdrant",
    collection="rag_chunks",
    top_k=20,
    rerank=True,
    rerank_top_k=5,
)
```

## Function

```python
RagRails().retrieve(
    query,
    *,
    vector_db="qdrant",
    collection=None,
    url=None,
    top_k=10,
    embedder="voyage",
    model="voyage-3",
    rerank=False,
    reranker="voyage",
    reranker_model="rerank-2-lite",
    rerank_top_k=5,
)
```

### `retrieve()` Parameters

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `query` | `str` | - | Yes | Query text to search for. |
| `vector_db` | `"qdrant" \| "pinecone" \| "weaviate"` | `"qdrant"` | No | Vector database provider to search. |
| `collection` | `str \| None` | `None` | No | Collection, index, or class name. Provider defaults apply when omitted. |
| `url` | `str \| None` | `None` | No | Vector database URL. Useful for local Qdrant or Weaviate. |
| `top_k` | `int` | `10` | No | Number of vector search candidates to return. |
| `embedder` | `str` | `"voyage"` | No | Query embedding provider. |
| `model` | `str` | `"voyage-3"` | No | Query embedding model. |
| `rerank` | `bool` | `False` | No | Rerank retrieved candidates. |
| `reranker` | `str` | `"voyage"` | No | Reranker provider. |
| `reranker_model` | `str` | `"rerank-2-lite"` | No | Reranker model. |
| `rerank_top_k` | `int` | `5` | No | Number of reranked results to return. |

## Result

```python
RetrieveResult(
    query=str,
    results=[
        RetrievedChunk(
            id=str,
            score=float,
            text=str,
            metadata=dict,
            rerank_score=float | None,
        )
    ],
)
```

## Stage Runner

The lower-level stage runner still works:

```bash
uv run python -m ragrails.pipeline.stg_04_retriever "How do payouts work?"
```
