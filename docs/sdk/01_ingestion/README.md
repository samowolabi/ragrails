# Ingestion

Ragrails ingestion turns external content into clean markdown.

Current ingestion SDK methods:

- [URL ingestion](url/README.md): `RagRails().scrape(...)`
- [Document ingestion](documents/README.md): `RagRails().parse(...)`
- [API ingestion](api/README.md): `RagRails().fetch(...)`

## Install

Document and API ingestion are included with the base install:

```bash
pip install ragrails
```

URL ingestion uses a separate install because browser-backed crawling pulls in
heavier crawler dependencies.

After installing URL ingestion, run URL setup once in the same Python
environment:

```python
from ragrails import RagRails

RagRails().setup_url()
```

This also works in Jupyter because it uses the active kernel's Python
executable.

## URL Ingestion

Use URL ingestion when your source content is a web page or website.

Install:

```bash
pip install "ragrails[url]"
```

Run this because URL ingestion needs it to load web pages, execute browser-backed crawling, and convert the page content into markdown.

```python
from ragrails import RagRails

rag = RagRails()
rag.setup_url()

result = rag.scrape(
    url="https://example.com",
    mode="full",
    output_dir="files/output/web_crawled",
)
```

Retry failed URLs from the scrape DLQ:

```python
result = rag.retry_scrape(
    "files/output/web_crawled/dlq.json",
)
```

### URL Parameters

| Method | Parameter | Type | Default | Required | Description |
|---|---|---|---:|---|---|
| `setup_url()` | `browser` | `str` | `"chromium"` | No | Playwright browser binary to install for URL scraping. |
| `scrape()` | `url` | `str \| list[str]` | - | Yes | URL or URLs to scrape. |
| `scrape()` | `mode` | `"each" \| "full"` | `"each"` | No | Scrape exact URLs or crawl full sites. |
| `scrape()` | `output_dir` | `str` | `"files/output/web_crawled"` | No | Markdown output folder. |
| `scrape()` | `frontmatter` | `bool` | `True` | No | Add source metadata to markdown files. |
| `scrape()` | `dlq_path` | `str \| None` | `None` | No | Custom DLQ file. Defaults to `<output_dir>/dlq.json`. |
| `scrape()` | `max_depth` | `int` | `3` | No | Crawl depth for `mode="full"`. |
| `scrape()` | `max_pages` | `int` | `200` | No | Maximum pages per site. |
| `retry_scrape()` | `dlq_path` | `str` | - | Yes | DLQ file to retry. |
| `retry_scrape()` | `mode` | `"each" \| "full"` | `"each"` | No | Retry exact pages or full-site crawls. |
| `retry_scrape()` | `max_depth` | `int` | `3` | No | Crawl depth for `mode="full"`. |
| `retry_scrape()` | `max_pages` | `int` | `200` | No | Maximum pages per site. |
| `retry_scrape()` | `max_attempts` | `int` | `3` | No | Retry entries below this attempt count. |

## Document Ingestion

Use document ingestion when your source content is a local PDF, DOCX, CSV, XLSX,
or similar file.

Install:

```bash
pip install ragrails
```

No extra is required. Document ingestion ships with the base install.

```python
from ragrails import RagRails

result = RagRails().parse(
    files=["guide.pdf", "pricing.csv"],
    input_dir="files/input",
    output_dir="files/output/docs",
)
```

### Document Parameters

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `files` | `str \| list[str \| dict] \| None` | `None` | Conditional | Specific files to parse. |
| `folder` | `str \| None` | `None` | Conditional | Folder of supported documents to parse. |
| `input_dir` | `str` | `"files/input"` | No | Base folder for `files`. |
| `output_dir` | `str` | `"files/output/docs"` | No | Markdown output folder. |
| `frontmatter` | `bool` | `True` | No | Add document metadata to markdown files. |

## API Ingestion

Use API ingestion when your source content is a REST API response.

Install:

```bash
pip install ragrails
```

No extra is required. API ingestion ships with the base install.

```python
from ragrails import RagRails

result = RagRails().fetch(
    url="https://api.example.com/v1/products",
    title="Products",
    output_dir="files/output/api",
)
```

### API Parameters

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `url` | `str` | - | Yes | API endpoint URL. |
| `title` | `str` | `"API Response"` | No | Output metadata title. |
| `description` | `str` | `""` | No | Output metadata description. |
| `method` | `str` | `"GET"` | No | HTTP method. |
| `headers` | `dict \| None` | `None` | No | Request headers. |
| `params` | `dict \| None` | `None` | No | Query parameters. |
| `body` | `dict \| None` | `None` | No | JSON request body. |
| `pagination` | `dict \| None` | `None` | No | Pagination configuration. |
| `max_pages` | `int` | `100` | No | Maximum API pages to fetch. |
| `output_dir` | `str` | `"files/output/api"` | No | Markdown output folder. |
| `frontmatter` | `bool` | `True` | No | Add API metadata to markdown files. |
