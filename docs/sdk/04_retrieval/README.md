# Retrieval

The public Ragrails retrieval SDK nomenclature is not finalized yet.

For now, start with ingestion:

```python
from ragrails import RagRails

result = RagRails().scrape(
    url="https://example.com/docs",
    mode="full",
    output_dir="files/output/web_crawled",
)
```

Retrieval will be documented here after the public method name is chosen.
