# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

- Added smoke test coverage for SDK imports, CLI commands, server routes, local chunking, and docs structure.
- Added CLI integration tests for command wiring, option parsing, validation, and local chunk output.
- Added release helper scripts for test, build, and publish workflows.
- Added documentation references for Jupyter notebooks, Swagger UI, and OpenAPI schema usage.

### Changed

- Moved chunking and REST API server dependencies into the base install.
- Renamed the package interface layer from `ragrails/usage/` to `ragrails/interfaces/`.
- Clarified why optional provider and URL scraping extras still exist.

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
- Updated root and docs READMEs to point to the usage/stage documentation structure.

### Removed

- Removed the old root SDK wrapper module.
- Removed the old root CLI package wrapper.
