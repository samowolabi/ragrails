# SDK Chat

Run stateless RAG chat over a stored retrieval index.

Chat does not keep hidden state. Pass `history` explicitly and store the returned
`result.history` in your application session.

## Basic Usage

```python
from ragrails import (
    ChatRetrievalQualityConfig,
    HistoryCompactionConfig,
    IntentRoutingConfig,
    QueryRewriteConfig,
    RagRails,
)

rag = RagRails()

llm = rag.llm(provider="openai", model="gpt-4.1-mini")
query_embedder = rag.embedder(provider="voyage", model="voyage-3", input_type="query")

history = []

result = rag.chat(
    "How do I authenticate?",
    llm=llm,
    embedder=query_embedder,
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
    history=history,
)

print(result.answer)
history = result.history
```

## Result Shape

```python
result.answer
result.sources
result.history
result.retrieval
result.retrieval_quality
result.answer_confidence
result.llm
result.errors
result.intent
result.compacted
```

Each source includes retrieval and rerank scores when available:

```python
{
    "id": "C1",
    "chunk_id": "chunk-id",
    "title": "Authentication",
    "path": "https://docs.example.com/auth",
    "retrieval_score": 0.82,
    "rerank_score": 0.91,
}
```

## Retrieval Quality

Retrieval quality controls which chunks are trusted enough to become chat
context. If reranking ran, `min_rerank_score` is used. Otherwise,
`min_retrieval_score` is used.

```python
quality = ChatRetrievalQualityConfig(
    min_retrieval_score=0.35,
    min_rerank_score=0.50,
    low_confidence_mode="answer_with_caution",
    max_context_chunks=5,
)

result = rag.chat(
    "How do I authenticate?",
    llm=llm,
    embedder=query_embedder,
    retrieval_quality=quality,
)
```

Low-confidence modes:

- `"answer_with_caution"`: answer carefully without claiming retrieved context supports the answer.
- `"ask_clarifying_question"`: ask one concise clarifying question.
- `"refuse_grounded_answer"`: return a natural “not enough relevant context” response.
- `"return_no_answer"`: return an empty answer and add a quality error.

Quality metadata is returned as:

```python
result.retrieval_quality
```

Answer confidence metadata is returned as:

```python
result.answer_confidence
```

The confidence level is derived from retrieval quality, source count, retrieval
score, rerank score, low-confidence mode, and errors.

## History Compaction

Default compaction starts when returned history reaches 15 messages. It
summarizes the older 10 messages and keeps the most recent 5 messages.

```python
history_config = HistoryCompactionConfig(
    enabled=True,
    history_limit=15,
    keep_recent=5,
)

result = rag.chat(
    "Continue",
    llm=llm,
    embedder=query_embedder,
    history=history,
    history_compaction=history_config,
)

history = result.history
```

Disable compaction:

```python
rag.chat(
    "Continue",
    llm=llm,
    embedder=query_embedder,
    history=history,
    history_compaction=HistoryCompactionConfig(enabled=False),
)
```

## Query Rewrite

Query rewrite is useful when the user asks a follow-up question that depends on
conversation context.

```python
rewrite = QueryRewriteConfig(
    enabled=True,
    session_context="User is asking about authentication",
    llm=rewrite_llm,  # optional; defaults to the chat llm
)

result = rag.chat(
    "How do I do it?",
    llm=llm,
    embedder=query_embedder,
    history=history,
    persona="Product knowledge base",
    query_rewrite=rewrite,
)
```

## Intent Routing

Small-talk messages bypass retrieval and go directly to the LLM. This includes
greetings, thanks, farewells, and acknowledgements such as:

- `hello`
- `thank you`
- `bye`
- `got it`

The detected intent is returned as:

```python
result.intent
```

Disable intent routing:

```python
rag.chat(
    "hello",
    llm=llm,
    embedder=query_embedder,
    intent_routing=IntentRoutingConfig(enabled=False),
)
```
