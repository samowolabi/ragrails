# SDK

The Python SDK is the core Ragrails interface. The CLI and REST API server call
the same SDK methods internally.

## Jupyter Notebooks

The repository includes notebooks for interactive SDK workflows:

| Notebook | Stage |
|---|---|
| `../../playground/notebooks/00_setup.ipynb` | Setup |
| `../../playground/notebooks/01_ingestors_url.ipynb` | URL ingestor |
| `../../playground/notebooks/02_ingestors_docs.ipynb` | Document ingestor |
| `../../playground/notebooks/03_ingestors_api.ipynb` | API ingestor |
| `../../playground/notebooks/04_ingestion.ipynb` | Ingestion |
| `../../playground/notebooks/05_chunking.ipynb` | Chunking |
| `../../playground/notebooks/06_embedding.ipynb` | Embedding |
| `../../playground/notebooks/07_storing.ipynb` | Storing |
| `../../playground/notebooks/08_retrieval.ipynb` | Retrieval |
| `../../playground/notebooks/09_chat.ipynb` | Chat |
| `../../playground/notebooks/10_pipeline.ipynb` | Pipeline |

## Stages

| Stage | SDK method | Docs |
|---|---|---|
| Ingestion | `scrape`, `parse`, `fetch` | [Ingestion](ingestion/README.md) |
| Chunking | `chunk` | [Chunking](chunking/README.md) |
| Embedding | `embed` | [Embedding](embedding/README.md) |
| Storing | `store`, `edit`, `delete` | [Storing](storing/README.md) |
| Retrieval | `retrieve` | [Retrieval](retrieval/README.md) |
| Pipeline | `ingest`, `query` | [Playground](../../playground/notebooks/README.md) |
