# URL Ingestion

Use `RagRails().scrape()` to scrape web pages into markdown files.

## Install

```bash
pip install "ragrails[url]"
```

Run this only when you need URL ingestion. The base `ragrails` install already
includes document and API ingestion, but URL crawling needs `crawl4ai`, which is
kept separate because it pulls in browser automation dependencies.

`crawl4ai` pulls in Playwright as a package dependency, but Playwright browser
binaries are downloaded separately. Run URL setup once in the same Python
environment that will run scraping:

```python
from ragrails import RagRails

rag = RagRails()
rag.setup_url()

result = rag.scrape(
    url="https://example.com/about",
    mode="each",
    output_dir="files/output/web_crawled",
)

print(result.pages)
print(result.files)
print(result.errors)
```

If you prefer the direct Playwright command:

```bash
python -m playwright install chromium
```

### `setup_url()` Parameters

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `browser` | `str` | `"chromium"` | No | Playwright browser binary to install for URL scraping. |

## Scrape Exact URLs

Use `mode="each"` when you only want the exact URL or URLs you pass in.

```python
from ragrails import RagRails

result = RagRails().scrape(
    url=[
        "https://example.com/about",
        "https://example.com/pricing",
    ],
    mode="each",
    output_dir="files/output/web_crawled",
)
```

## Crawl a Site

Use `mode="full"` when you want to crawl an entire website.

```python
from ragrails import RagRails

result = RagRails().scrape(
    url="https://example.com",
    mode="full",
    output_dir="files/output/web_crawled",
    max_depth=3,
    max_pages=200,
)
```

## Output

The ingestor writes markdown files:

```text
files/output/web_crawled/
  001_index.md
  002_about.md
  003_pricing.md
```

Each file includes frontmatter metadata such as:

- `path`
- `title`
- `description`
- `original_type`
- `status_code`

## Function

```python
RagRails().scrape(
    url,
    *,
    mode="each",
    output_dir="files/output/web_crawled",
    frontmatter=True,
    dlq_path=None,  # defaults to "<output_dir>/dlq.json"
    max_depth=3,
    max_pages=200,
)
```

### `scrape()` Parameters

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `url` | `str \| list[str]` | - | Yes | One URL or a list of URLs to scrape. Must be absolute `http` or `https` URLs. |
| `mode` | `"each" \| "full"` | `"each"` | No | `each` scrapes only the supplied URLs. `full` crawls each URL's site. |
| `output_dir` | `str` | `"files/output/web_crawled"` | No | Folder where markdown files are written. |
| `frontmatter` | `bool` | `True` | No | Adds source metadata to the top of each markdown file. |
| `dlq_path` | `str \| None` | `None` | No | Custom dead-letter queue file. If omitted, uses `<output_dir>/dlq.json`. |
| `max_depth` | `int` | `3` | No | Maximum crawl depth for `mode="full"`. |
| `max_pages` | `int` | `200` | No | Maximum pages to crawl per site for `mode="full"`. |

## Result

`scrape()` returns a `ScrapeResult`:

```python
print(result.pages)
print(result.failed)
print(result.output_dir)
print(result.files)
print(result.dlq_path)
print(result.errors)
```

## Validation

`scrape()` validates inputs before starting the browser.

It raises `ValueError` when:

- `url` is empty.
- any URL is not an absolute `http` or `https` URL.
- `mode` is not `each` or `full`.
- `output_dir` or `dlq_path` is empty.
- `max_depth` is negative.
- `max_pages` is less than `1`.

```python
from ragrails import RagRails

RagRails().scrape(
    url="example.com/about",
)
# ValueError: Invalid URL 'example.com/about' — use an absolute http(s) URL
```

## Error Handling

Failed crawls are recorded in the returned result.

```python
result = RagRails().scrape(
    url="https://example.com",
    mode="full",
)

if result.failed:
    print(result.errors)
```

The dead-letter queue path is available as `result.dlq_path`.
By default it is written to `dlq.json` inside the selected `output_dir`.
You can also pass `dlq_path` to write failures to a custom file.

## Retry Failed URLs

Use `retry_scrape()` to retry URLs saved in the dead-letter queue.

```python
from ragrails import RagRails

rag = RagRails()

result = rag.retry_scrape(
    "files/output/web_crawled/dlq.json",
)

print(result.pages)
print(result.failed)
print(result.dlq_path)
print(result.errors)
```

### `retry_scrape()` Parameters

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `dlq_path` | `str` | - | Yes | Path to the DLQ file to retry, for example `files/output/web_crawled/dlq.json`. |
| `mode` | `"each" \| "full"` | `"each"` | No | Retry URLs as exact pages or full-site crawls. |
| `max_depth` | `int` | `3` | No | Maximum crawl depth for `mode="full"`. |
| `max_pages` | `int` | `200` | No | Maximum pages to crawl per site for `mode="full"`. |
| `max_attempts` | `int` | `3` | No | Only retry DLQ entries with fewer than this many attempts. |

`retry_scrape()` infers the retry output directory from the DLQ path's folder.
For example, `files/output/web_crawled/dlq.json` retries into
`files/output/web_crawled`.

If you want to retry a different DLQ file, pass that path explicitly:

```python
scrape_result = RagRails().scrape(
    url="https://example.com",
    output_dir="files/output/web_crawled",
    dlq_path="files/output/custom/dlq.json",
)

result = RagRails().retry_scrape(
    "files/output/custom/dlq.json",
)
```
