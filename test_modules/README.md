# Manual Module Tests

These files are quick module-level checks you can run directly while developing.
They are separate from the automated `tests/` suite.

Run from the repo root:

```bash
uv run python test_modules/core_chunking.py
uv run python test_modules/core_ingestion_api.py
uv run python test_modules/core_ingestion_docs_array.py
uv run python test_modules/core_ingestion_docs_bytes.py
uv run python test_modules/core_ingestion_url.py
```

`core_ingestion_url.py` requires URL scraping dependencies and Playwright browser
setup:

```bash
uv run python -c "from ragrails import RagRails; RagRails().setup_url()"
```
