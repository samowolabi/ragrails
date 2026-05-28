# REST API Chunking

Chunking accepts markdown text and returns JSON chunks in the response.

## Endpoint

```text
POST /v1/chunk
```

## Request

```bash
curl -X POST http://127.0.0.1:8000/v1/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "markdown": [
      {
        "markdown": "# Auth\n\nUse a bearer token.",
        "title": "Auth",
        "source": "https://docs.example.com/auth"
      },
      {
        "markdown": "# Billing\n\nInvoices are generated monthly.",
        "title": "Billing",
        "source": "https://docs.example.com/billing"
      }
    ]
  }'
```

## Response

The response includes `items`, an array of chunk dictionaries with `text`,
`embed_text`, and `metadata`.

Back to the [REST API overview](../README.md).
