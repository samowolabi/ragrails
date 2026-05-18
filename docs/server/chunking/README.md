# REST API Chunking

Chunking splits markdown files into chunk JSON files.

## Endpoint

```text
POST /v1/chunk
```

## Request

```bash
curl -X POST http://127.0.0.1:8000/v1/chunk \
  -H "Content-Type: application/json" \
  -d '{
    "input_dir": "files/output/api",
    "output_dir": "files/output/chunks/api"
  }'
```

Chunking requires the chunk extra:

```bash
pip install "ragrails[server,chunk]"
```

Back to the [REST API overview](../README.md).
