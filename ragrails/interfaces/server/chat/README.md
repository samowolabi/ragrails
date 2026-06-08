# REST Chat

SDK-backed chat route.

| Endpoint | SDK method |
|---|---|
| `POST /v1/chat` | `RagRails().chat()` |
| `POST /v1/chat/stream` | `RagRails().chat_stream()` |

REST chat is stateless. Pass `history` in the request and persist the returned
`history` in the client application.

## Streaming

Use `POST /v1/chat/stream` to receive server-sent events for normal RAG chat.
Events include retrieval progress, answer `token` chunks, and a final
`ChatResult`.

```bash
curl -N -X POST http://localhost:8000/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"query":"How do I authenticate?","collection":"docs"}'
```

## LLM Providers

OpenAI, Anthropic, and Google Gemini are included in the base Ragrails install.
Configure the provider you use with environment variables:

```bash
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...
```

Request payloads can select the LLM provider and model. Unknown model names are
allowed when the provider is explicit, which lets the API use new provider
models before the local pricing catalog is updated.
