# CLI Chat

Command for RAG chat from the terminal.

## Command

| Command | SDK method | Purpose |
|---|---|---|
| `chat` | `RagRails().chat()` | Run one SDK-backed chat turn. |

## One-shot Chat

```bash
ragrails chat "How do payouts work?" \
  --vector-db qdrant \
  --collection rag_chunks \
  --llm-provider openai \
  --llm-model gpt-4.1-mini
```

Use a history file for explicit stateless sessions:

```bash
ragrails chat "How do payouts work?" --history-file files/chat/history.json
ragrails chat "What about refunds?" --history-file files/chat/history.json --rewrite-query
```

## Interactive Mode

```bash
ragrails chat
```

With no query argument, the command starts the existing interactive chat app.
