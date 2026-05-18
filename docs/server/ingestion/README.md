# REST API Ingestion

Ingestion endpoints turn external sources into markdown files.

## Endpoints

| Endpoint | Description |
|---|---|
| `POST /v1/ingest/api` | Fetch a REST API endpoint into markdown |
| `POST /v1/ingest/url` | Scrape URLs into markdown |
| `POST /v1/ingest/docs` | Convert local documents into markdown |

## API Ingestion

```bash
curl -X POST http://127.0.0.1:8000/v1/ingest/api \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.example.com/v1/products",
    "title": "Products",
    "headers": {
      "Authorization": "Bearer <token>"
    },
    "params": {
      "limit": 100
    },
    "output_dir": "files/output/api",
    "max_pages": 10
  }'
```

## URL Ingestion

URL ingestion requires the URL extra and browser setup:

```bash
pip install "ragrails[server,url]"
ragrails setup-url
```

```bash
curl -X POST http://127.0.0.1:8000/v1/ingest/url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "mode": "full",
    "output_dir": "files/output/web_crawled",
    "max_pages": 50
  }'
```

## Document Ingestion

```bash
curl -X POST http://127.0.0.1:8000/v1/ingest/docs \
  -H "Content-Type: application/json" \
  -d '{
    "folder": "files/input",
    "output_dir": "files/output/docs"
  }'
```

Back to the [REST API overview](../README.md).
