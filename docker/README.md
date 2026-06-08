# Ragrails Docker

Run the Ragrails REST API in Docker.

The Docker runtime is centered on the API:

```text
ragrails-api -> FastAPI server -> SDK -> core
```

The default Compose setup starts:

- `ragrails-api` on `http://localhost:8000`
- `qdrant` on `http://localhost:6333`

## Setup

Copy the environment template:

```bash
cp docker/env/api.env.example docker/env/api.env
```

Set the provider keys you need in `docker/env/api.env`.

For the default Qdrant workflow, set at least:

```env
VOYAGE_API_KEY=
OPENAI_API_KEY=
VECTOR_DB_PROVIDER=qdrant
VECTOR_DB_URL=http://qdrant:6333
VECTOR_DB_COLLECTION=rag_chunks
```

## Start

Run from the repository root:

```bash
docker compose -f docker/compose/compose.yaml --env-file docker/env/api.env up --build
```

Run in the background:

```bash
docker compose -f docker/compose/compose.yaml --env-file docker/env/api.env up --build -d
```

## Check

Health endpoint:

```bash
curl http://localhost:8000/v1/health
```

Swagger UI:

```text
http://localhost:8000/docs
```

OpenAPI schema:

```text
http://localhost:8000/v1/openapi.json
```

## Logs

```bash
docker compose -f docker/compose/compose.yaml --env-file docker/env/api.env logs -f ragrails-api
```

## Stop

```bash
docker compose -f docker/compose/compose.yaml --env-file docker/env/api.env down
```

Remove Qdrant data too:

```bash
docker compose -f docker/compose/compose.yaml --env-file docker/env/api.env down -v
```

## Image

Build only the API image:

```bash
docker build -f docker/api/Dockerfile -t ragrails-api:local .
```

Run only the API container against an external Qdrant:

```bash
docker run --rm -p 8000:8000 \
  --env-file docker/env/api.env \
  -e VECTOR_DB_URL=http://host.docker.internal:6333 \
  ragrails-api:local
```

## Notes

- The default image installs the local package with API, Qdrant, and URL ingestion extras. Built-in OpenAI, Anthropic, and Google LLM support comes from the base package.
- URL ingestion uses Playwright through `crawl4ai`; Chromium is installed during the image build.
- Reranking is intentionally not included in the default image because it pulls a much heavier ML stack. Use a dedicated image variant later if you need local reranking in Docker.
- URL ingestion may need browser setup support in a later image variant.
- For production, pin a versioned image tag instead of `ragrails-api:local`.
