#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

UV="${UV:-uv}"
RUN=("$UV" run --locked --extra server --extra chunk)

section() {
  printf "\n==> %s\n" "$1"
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf "Missing required command: %s\n" "$1" >&2
    exit 1
  fi
}

require_command "$UV"

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

section "Python package imports and public SDK surface"
"${RUN[@]}" python - <<'PY'
from ragrails import (
    ApiIngestResult,
    ChunkResult,
    EmbedResult,
    ParseResult,
    RagRails,
    RetrieveResult,
    RetrievedChunk,
    ScrapeResult,
    StoreResult,
)

rag = RagRails()
expected_methods = [
    "setup_url",
    "scrape",
    "retry_scrape",
    "parse",
    "fetch",
    "chunk",
    "chunk_file",
    "embed",
    "store",
    "retrieve",
]

missing = [name for name in expected_methods if not callable(getattr(rag, name, None))]
if missing:
    raise AssertionError(f"Missing SDK methods: {missing}")

_ = [
    ScrapeResult,
    ParseResult,
    ApiIngestResult,
    ChunkResult,
    EmbedResult,
    StoreResult,
    RetrieveResult,
    RetrievedChunk,
]

print("SDK imports and methods OK")
PY

section "Compile package modules"
"${RUN[@]}" python -m compileall -q ragrails

section "CLI entrypoint and command help"
"${RUN[@]}" ragrails --help >/dev/null
for command in setup-url scrape parse fetch chunk chunk-file embed store retrieve; do
  "${RUN[@]}" ragrails "$command" --help >/dev/null
done
printf "CLI help commands OK\n"

section "Chunking pipeline with local markdown"
mkdir -p "$TMP_DIR/input" "$TMP_DIR/chunks"
cat > "$TMP_DIR/input/guide.md" <<'MD'
---
title: Smoke Guide
path: https://example.com/smoke-guide
---

# Smoke Guide

This markdown file is used by the smoke test to verify that the chunking stage
can read local markdown, preserve useful metadata, and write JSON chunk output.

## Details

The content is intentionally small, local, and deterministic so the smoke test
does not need network access, API keys, browser setup, or a vector database.
MD

"${RUN[@]}" ragrails chunk \
  --input-dir "$TMP_DIR/input" \
  --output-dir "$TMP_DIR/chunks" \
  --chunk-size 400 \
  --chunk-overlap 40 \
  --min-chunk-length 20 >/dev/null

"${RUN[@]}" python - "$TMP_DIR/chunks/guide.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    raise AssertionError(f"Expected chunk output not found: {path}")

chunks = json.loads(path.read_text())
if not chunks:
    raise AssertionError("Expected at least one chunk")

first = chunks[0]
if "text" not in first or "metadata" not in first or "embed_text" not in first:
    raise AssertionError(f"Unexpected chunk shape: {first.keys()}")

metadata = first["metadata"]
if metadata.get("title") != "Smoke Guide":
    raise AssertionError(f"Expected title metadata to be preserved, got: {metadata}")

print(f"Chunk output OK: {len(chunks)} chunk(s)")
PY

section "REST API app, routes, and validation"
"${RUN[@]}" python - <<'PY'
from fastapi.testclient import TestClient

from ragrails.usage.server.app import create_app

app = create_app()
schema = app.openapi()
paths = set(schema["paths"])
expected_paths = {
    "/v1/health",
    "/v1/ingest/api",
    "/v1/ingest/url",
    "/v1/ingest/docs",
    "/v1/chunk",
    "/v1/embed",
    "/v1/store",
    "/v1/retrieve",
}

missing = sorted(expected_paths - paths)
if missing:
    raise AssertionError(f"Missing REST routes: {missing}")

client = TestClient(app)

health = client.get("/v1/health")
if health.status_code != 200:
    raise AssertionError(f"Health endpoint failed: {health.status_code} {health.text}")

invalid_chunk = client.post("/v1/chunk", json={"input_dir": "/path/that/does/not/exist"})
if invalid_chunk.status_code < 400:
    raise AssertionError(f"Expected invalid chunk request to fail, got {invalid_chunk.status_code}")

invalid_retrieve = client.post("/v1/retrieve", json={"query": ""})
if invalid_retrieve.status_code < 400:
    raise AssertionError(f"Expected invalid retrieve request to fail, got {invalid_retrieve.status_code}")

print("REST API routes and validation OK")
PY

section "Docs link sanity"
for path in \
  docs/README.md \
  docs/sdk/README.md \
  docs/sdk/ingestion/README.md \
  docs/sdk/chunking/README.md \
  docs/sdk/embedding/README.md \
  docs/sdk/storing/README.md \
  docs/sdk/retrieval/README.md \
  docs/cli/README.md \
  docs/cli/ingestion/README.md \
  docs/cli/chunking/README.md \
  docs/cli/embedding/README.md \
  docs/cli/storing/README.md \
  docs/cli/retrieval/README.md \
  docs/server/README.md \
  docs/server/ingestion/README.md \
  docs/server/chunking/README.md \
  docs/server/embedding/README.md \
  docs/server/storing/README.md \
  docs/server/retrieval/README.md; do
  test -f "$path"
done

if rg -n "docs/sdk/01|docs/sdk/02|docs/sdk/03|docs/sdk/04|docs/sdk/cli|docs/sdk/server|sdk/01_ingestion|sdk/02_chunking|sdk/03_embedding|sdk/04_retrieval|sdk/cli|sdk/server" README.md docs >/dev/null; then
  printf "Found stale docs links\n" >&2
  rg -n "docs/sdk/01|docs/sdk/02|docs/sdk/03|docs/sdk/04|docs/sdk/cli|docs/sdk/server|sdk/01_ingestion|sdk/02_chunking|sdk/03_embedding|sdk/04_retrieval|sdk/cli|sdk/server" README.md docs >&2
  exit 1
fi
printf "Docs structure OK\n"

section "Smoke test passed"
