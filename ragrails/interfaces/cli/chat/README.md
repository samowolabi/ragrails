# CLI Chat

Command for RAG chat from the terminal.

## Command

| Command | SDK method | Purpose |
|---|---|---|
| `chat` | `RagRails().chat()` | Run one SDK-backed chat turn. |

## LLM Providers

OpenAI, Anthropic, and Google Gemini are available from the base Ragrails
install. Set the API key for the provider you use:

```bash
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export GEMINI_API_KEY=...
```

Choose the provider and model with `--llm-provider` and `--llm-model`.

## One-shot Chat

```bash
ragrails chat "How do payouts work?" \
  --vector-db qdrant \
  --collection rag_chunks \
  --llm-provider openai \
  --llm-model gpt-4o-mini
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
