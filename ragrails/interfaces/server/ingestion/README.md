# REST Ingestion

SDK-backed ingestion routes.

| Endpoint | SDK method |
|---|---|
| `POST /v1/ingest/api` | `RagRails().fetch()` |
| `POST /v1/ingest/url` | `RagRails().scrape()` |
| `POST /v1/ingest/docs` | `RagRails().parse()` |

Responses return in-memory `outputs`; file output is not the REST default.
