# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.2.1] - 2026-06-04

### Added

- Added `ingest()` and `query()` pipeline convenience methods to the SDK — run the full ingestion, chunking, embedding, and storage pipeline in one call.
- Added `edit()` and `delete()` methods to the SDK for updating and removing stored chunks by ID.
- Added `llm()` factory method to the SDK for creating LLM provider objects.
- Added `answer_confidence` field to `ChatResult` — structured confidence assessment returned alongside every chat response.
- Added `DLQ` (dead-letter queue) support to `scrape()` — capture retryable failures in memory or to a file, and retry them in a subsequent call.
- Added `StoreResult`, `EditResult`, `DeleteResult`, `EmbedResult`, `RetrieveResult`, `IngestPipelineResult` result types to the public SDK exports.
- Added vector store lifecycle adapters for edit and delete across Qdrant, Pinecone, and Weaviate.
- Added SDK pipeline module (`ragrails/interfaces/sdk/pipeline/`) with `ingest()` and `query()` implementations and full test coverage.
- Added CLI `chat` command — SDK-backed one-shot chat turn with full options: `--llm-provider`, `--llm-model`, `--embedder-provider`, `--vector-db`, `--collection`, `--persona`, `--history-file`, `--rewrite-query`, `--rerank`, and more. Falls back to the interactive REPL when no query is given.
- Added CLI `ingest` and `query` pipeline commands — full pipeline in one command.
- Added CLI `edit` and `delete` commands to the `store` module.
- Added `--output-dir` option to `scrape`, `parse`, and `fetch` CLI commands — saves output as JSON files for stage-by-stage workflows.
- Added REST API `/v1/chat` endpoint — stateless chat turn over the SDK.
- Added REST API `/v1/pipelines/ingest` and `/v1/pipelines/query` endpoints — SDK pipeline in a single request.
- Added `server`, `server-qdrant`, `server-pinecone`, and `server-weaviate` optional extras — install only what the REST API stack needs.
- Added per-module `tests/` packages for all CLI commands and REST API services.
- Added `README.md` files inside each CLI and REST API module.
- Added release helper scripts: `scripts/test-core.sh`, `scripts/test-sdk.sh`, `scripts/test-cli.sh`, `scripts/test-rest.sh`.
- Added pre-push git hook (`.githooks/pre-push`) — runs all interface checks before each push.

### Changed

- Refactored CLI to be fully SDK-backed — all command modules call `RagRails()` directly; no direct core imports.
- Refactored CLI `embed` command — now reads chunk JSON files from `--input-dir` and writes embedded JSON to `--output-dir`. Removed `--vector-db`, `--collection`, and `--url` (embedding is now separate from storage).
- Refactored CLI `store` command — now reads embedded JSON from `--input-dir`. Removed `--embedder` and `--model` options.
- Refactored CLI `chunk` command — now reads ingestion output JSON from `--input-dir` instead of taking `--markdown` text directly.
- Refactored CLI `retrieve` command — renamed `--embedder`/`--model` to `--provider`/`--model` to match SDK conventions. Now creates embedder and reranker objects internally.
- Refactored REST API services to call `RagRails()` — no direct core imports in the server layer.
- Updated `print_errors` in CLI common to handle both `list[str]` and `list[dict]` error formats.
- Updated `QueryRewriteConfig` — replaced `rewrite_context` with `llm` field for specifying a separate LLM for query rewriting; `persona` is now used as the rewrite context.
- Replaced old `notebooks/` folder with a dedicated `playground/notebooks/` set organized by SDK stage (`00_setup` through `10_pipeline`).
- Replaced old `test_modules/` manual scripts with proper per-module unit tests.
- Updated `pyproject.toml` to add `server` extras and separate REST API dependencies from the SDK base install.

### Removed

- Removed old docs directory (`docs/`) — documentation now lives alongside each module as `README.md` files.
- Removed old integration test file `tests/cli/test_cli_integration.py` — replaced by per-module unit tests.
- Removed `test_modules/` manual test scripts.
- Removed eval fixture files (`files/eval/`).

## [0.2.0] - 2026-06-04

### Added

- Initial major refactor: reorganized all pipeline stages under `ragrails/core/` (`stg_01` through `stg_06`) and all public interfaces under `ragrails/interfaces/`.
- Added public SDK (`RagRails`) with methods for ingestion, chunking, embedding, storing, retrieval, and chat.
- Added `scrape()`, `parse()`, `fetch()`, `chunk()`, `embedder()`, `embed()`, `store()`, `reranker()`, `retrieve()`, `chat()` to the public SDK.
- Added `ChatResult` with `retrieval_quality`, `answer_confidence`, `compacted`, and `intent` fields.
- Added `QueryRewriteConfig`, `HistoryCompactionConfig`, `IntentRoutingConfig`, `ChatRetrievalQualityConfig` config objects.
- Added `ScrapeResult`, `ParseResult`, `ApiIngestResult`, `ChunkResult` result types.

### Changed

- Renamed `ragrails/pipeline/` to `ragrails/core/`.
- Renamed `ragrails/usage/` to `ragrails/interfaces/`.

## [0.1.10] - 2026-05-18

### Added

- Added stage-based interface implementation under `ragrails/interfaces/` for SDK, CLI, and REST API server.
- Added REST API server support with FastAPI.
- Added SDK, CLI, and REST API docs organized by ingestion, chunking, embedding, storing, and retrieval.
- Added public SDK methods for embedding, storing, and retrieval.
- Added public result types for embedding and retrieval responses.

### Changed

- Reorganized CLI implementation by pipeline stage.
- Reorganized SDK implementation by pipeline stage.
- Updated package entrypoints to use the new `ragrails/interfaces/` modules.

### Removed

- Removed the old root SDK wrapper module.
- Removed the old root CLI package wrapper.
