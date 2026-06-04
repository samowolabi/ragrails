# REST Interface

FastAPI interface over the public SDK. Route services should call
`ragrails.interfaces.sdk.RagRails` and avoid direct core calls.

## Modules

| Module | Endpoints |
|---|---|
| `health` | `/v1/health` |
| `ingestion` | `/v1/ingest/api`, `/v1/ingest/url`, `/v1/ingest/docs` |
| `chunking` | `/v1/chunk` |
| `embedding` | `/v1/embed` |
| `storing` | `/v1/store`, `/v1/edit`, `/v1/delete` |
| `retrieval` | `/v1/retrieve` |
| `pipeline` | `/v1/pipelines/ingest`, `/v1/pipelines/query` |
| `chat` | `/v1/chat` |

## Contract

- REST is SDK-backed.
- Request/response bodies are in-memory JSON by default.
- Do not require server-local input/output directories for the public API.
- Keep tests in each REST module under `tests/`.
