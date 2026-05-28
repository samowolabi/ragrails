# SDK Chat

Run stateless RAG chat.

Chat history is always explicit. Pass history as an array when you want a
conversation-aware turn, then store `result.history` wherever your application
keeps session state.

## Basic Usage

```python
from ragrails import RagRails
from ragrails.interfaces.sdk.chat import ChatRetrievalQualityConfig, HistoryCompactionConfig

rag = RagRails()

llm = rag.llm(provider="openai", model="gpt-4.1-mini")
query_embedder = rag.embedder(provider="voyage", model="voyage-3", input_type="query")

result = rag.chat(
    "How do I authenticate?",
    llm=llm,
    embedder=query_embedder,
    vector_db="qdrant",
    collection="docs",
    url="http://localhost:6333",
)

print(result.answer)
history = result.history
```

## Retrieval Quality

Use retrieval quality config to decide what chat should do when retrieved chunks
are weak.

```python
result = rag.chat(
    "How do I authenticate?",
    llm=llm,
    embedder=query_embedder,
    retrieval_quality=ChatRetrievalQualityConfig(
        min_retrieval_score=0.35,
        min_rerank_score=0.50,
        low_confidence_mode="answer_with_caution",
        max_context_chunks=5,
    ),
)
```

Low confidence modes:

- `"answer_with_caution"` asks the LLM to answer cautiously or ask for clarification.
- `"ask_clarifying_question"` asks the LLM to ask one concise clarifying question.
- `"refuse_grounded_answer"` returns a natural message that there is not enough relevant context.
- `"return_no_answer"` returns an empty answer and adds a quality error.

Quality metadata is returned as `result.retrieval_quality`.

## History Compaction

By default, `history_limit=15` and `history_keep_recent=5`. When the returned
history grows beyond 15 messages, the SDK summarizes older messages with the
provided LLM, clears those older messages from the returned history, and keeps:

- one system summary message
- the most recent 5 messages

```python
result = rag.chat(
    "Continue",
    llm=llm,
    embedder=query_embedder,
    history=history,
    history_compaction=HistoryCompactionConfig(
        enabled=True,
        history_limit=15,
        keep_recent=5,
    ),
)

print(result.compacted)
history = result.history
```

Disable compaction with:

```python
rag.chat(
    "Continue",
    llm=llm,
    embedder=query_embedder,
    history_compaction=HistoryCompactionConfig(enabled=False),
)
```

## Query Rewrite

Enable query rewriting when the user question depends on prior context:

```python
from ragrails.interfaces.sdk.chat import QueryRewriteConfig

result = rag.chat(
    "How do I do it?",
    llm=llm,
    embedder=query_embedder,
    history=history,
    query_rewrite=QueryRewriteConfig(
        enabled=True,
        rewrite_context="Product documentation",
        session_context="User is asking about authentication",
    ),
)
```

## User Intent

Small-talk messages such as greetings, thanks, farewells, and acknowledgements
bypass retrieval and go directly to the LLM. Examples include:

- `hello`
- `thank you`
- `bye`
- `got it`

The detected intent is returned as `result.intent`.

Disable intent routing with:

```python
from ragrails.interfaces.sdk.chat import IntentRoutingConfig

rag.chat(
    "hello",
    llm=llm,
    embedder=query_embedder,
    intent_routing=IntentRoutingConfig(enabled=False),
)
```
