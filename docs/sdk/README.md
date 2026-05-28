# SDK

The Python SDK is the core Ragrails interface. The CLI and REST API server call
the same SDK methods internally.

## Jupyter Notebooks

The repository includes notebooks for interactive SDK workflows:

| Notebook | Stage |
|---|---|
| `notebooks/01_ingestion.ipynb` | Ingestion |
| `notebooks/02_chunking.ipynb` | Chunking |
| `notebooks/03_embedding.ipynb` | Embedding |
| `notebooks/03_store.ipynb` | Storing |
| `notebooks/04_retrieval.ipynb` | Retrieval |

## Stages

| Stage | SDK method | Docs |
|---|---|---|
| Ingestion | `scrape`, `parse`, `fetch` | [Ingestion](ingestion/README.md) |
| Chunking | `chunk`, `chunk_file` | [Chunking](chunking/README.md) |
| Embedding | `embed` | [Embedding](embedding/README.md) |
| Storing | `store` | [Storing](storing/README.md) |
| Retrieval | `retrieve` | [Retrieval](retrieval/README.md) |
