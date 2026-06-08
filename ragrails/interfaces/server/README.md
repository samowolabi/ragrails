# REST Interface

FastAPI interface over the public SDK. Route services should call
`ragrails.interfaces.sdk.RagRails` and avoid direct core calls.

## Modules

| Module | Endpoints |
|---|---|
| `health` | `/v1/health` |
| `ingestion` | `/v1/ingest/api`, `/v1/ingest/url`, `/v1/ingest/url/stream`, `/v1/ingest/docs`, `/v1/ingest/docs/upload` |
| `chunking` | `/v1/chunk` |
| `embedding` | `/v1/embed` |
| `storing` | `/v1/store`, `/v1/edit`, `/v1/delete` |
| `retrieval` | `/v1/retrieve` |
| `pipeline` | `/v1/pipelines/ingest`, `/v1/pipelines/query` |
| `chat` | `/v1/chat`, `/v1/chat/stream` |

## Docker

The Docker setup runs this REST API as the container entrypoint.

```bash
cp docker/env/api.env.example docker/env/api.env
docker compose -f docker/compose/compose.yaml --env-file docker/env/api.env up --build
```

Swagger UI is available at:

```text
http://localhost:8000/docs
```

See [docker/README.md](../../../docker/README.md) for full Docker usage.

## Provider Configuration

Built-in LLM providers are installed with the base package. Configure the
provider you use with environment variables:

```bash
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...
```

Embedding and vector database providers still use their own extras and API keys,
for example `VOYAGE_API_KEY` and `VECTOR_DB_URL`.

## Contract

- REST is SDK-backed.
- Request/response bodies are in-memory JSON by default.
- Do not require server-local input/output directories for the public API.
- Keep tests in each REST module under `tests/`.
