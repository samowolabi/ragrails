# Ingestion

Ragrails ingestion turns external content into clean markdown.

Current ingestion SDK methods:

- [URL ingestion](url/README.md): `RagRails().scrape(...)`
- [Document ingestion](documents/README.md): `RagRails().parse(...)`
- [API ingestion](api/README.md): `RagRails().fetch(...)`

## Install

Install only the ingestion extra you need:

```bash
pip install "ragrails[url]"   # RagRails().scrape(...)
pip install "ragrails[docs]"  # RagRails().parse(...)
pip install "ragrails[api]"   # RagRails().fetch(...)
```

For all ingestion methods:

```bash
pip install "ragrails[url,docs,api]"
```

## URL Ingestion

Use URL ingestion when your source content is a web page or website.

```python
from ragrails import RagRails

result = RagRails().scrape(
    url="https://example.com",
    mode="full",
    output_dir="files/output/web_crawled",
)
```

## Document Ingestion

Use document ingestion when your source content is a local PDF, DOCX, CSV, XLSX,
or similar file.

```python
from ragrails import RagRails

result = RagRails().parse(
    files=["guide.pdf", "pricing.csv"],
    input_dir="files/input",
    output_dir="files/output/docs",
)
```

## API Ingestion

Use API ingestion when your source content is a REST API response.

```python
from ragrails import RagRails

result = RagRails().fetch(
    url="https://api.example.com/v1/products",
    title="Products",
    output_dir="files/output/api",
)
```
