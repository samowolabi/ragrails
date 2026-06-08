# REST Pipeline

SDK-backed pipeline routes.

| Endpoint | SDK method |
|---|---|
| `POST /v1/pipelines/ingest` | `RagRails().ingest()` |
| `POST /v1/pipelines/query` | `RagRails().query()` |

These endpoints are the lowest-hassle REST path for production clients.

`POST /v1/pipelines/ingest` accepts `concurrency`:

- `serial`: process `docs`, `urls`, and `api` sources one after another.
- `parallel`: process independent source groups concurrently, then merge before
  chunking, embedding, and storage.
