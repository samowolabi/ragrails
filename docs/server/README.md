# REST API Server

The Ragrails REST API gives non-Python clients a language-agnostic HTTP
interface over the same pipeline used by the SDK and CLI.

## Run

```bash
ragrails-api
```

The API listens on `http://127.0.0.1:8000` by default.

```bash
ragrails-api --host 0.0.0.0 --port 8080
```

Swagger UI and OpenAPI docs are available at:

```text
http://127.0.0.1:8000/docs
http://127.0.0.1:8000/v1/openapi.json
```

Use Swagger UI at `/docs` to inspect schemas and try endpoints from the browser.

## Stage Docs

| Stage | Endpoints | Docs |
|---|---|---|
| Ingestion | `/v1/ingest/api`, `/v1/ingest/url`, `/v1/ingest/docs` | [Ingestion](ingestion/README.md) |
| Chunking | `/v1/chunk` | [Chunking](chunking/README.md) |
| Embedding | `/v1/embed` | [Embedding](embedding/README.md) |
| Storing | `/v1/store` | [Storing](storing/README.md) |
| Retrieval | `/v1/retrieve` | [Retrieval](retrieval/README.md) |

## Health

```text
GET /v1/health
```

## Implementation Layout

```text
ragrails/interfaces/server/
  ingestion/
  chunking/
  embedding/
  storing/
  retrieval/
```

Back to the [docs index](../README.md).
