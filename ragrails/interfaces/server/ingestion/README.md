# REST Ingestion

SDK-backed ingestion routes.

| Endpoint | SDK method |
|---|---|
| `POST /v1/ingest/api` | `RagRails().fetch()` |
| `POST /v1/ingest/url` | `RagRails().scrape()` |
| `POST /v1/ingest/url/stream` | `RagRails().scrape_stream()` |
| `POST /v1/ingest/docs` | `RagRails().parse()` |
| `POST /v1/ingest/docs/upload` | `RagRails().parse()` |

Responses return in-memory `outputs`; file output is not the REST default.

## URL Stream

Use the streaming endpoint to receive crawl progress as server-sent events.
The final event contains the same aggregate shape as `POST /v1/ingest/url`.

```bash
curl -N -X POST http://localhost:8000/v1/ingest/url/stream \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com/docs","mode":"full"}'
```

Events include `progress`, `page`, `error`, and `final`.

## Document Upload

Use multipart form data when documents come from a browser, frontend app, or
API client instead of server-local paths.

```bash
curl -X POST http://localhost:8000/v1/ingest/docs/upload \
  -F "files=@docs/guide.pdf" \
  -F "frontmatter=false" \
  -F "description=Product guide"
```

Upload fields:

- `files`: one or more document files.
- `frontmatter`: optional boolean.
- `title`: optional title for single-file uploads.
- `description`: optional description stored in document metadata.
