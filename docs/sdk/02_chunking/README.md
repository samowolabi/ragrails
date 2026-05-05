# Chunking

The public Ragrails chunking SDK nomenclature is not finalized yet.

For now, start with ingestion:

```python
from ragrails import RagRails

result = RagRails().scrape(
    url="https://example.com/docs",
    mode="full",
    output_dir="files/output/web_crawled",
)
```

Chunking will be documented here after the public method name is chosen.
