# URL Ingestion

Use `RagRails().scrape()` to scrape web pages into markdown files.

## Install

```bash
pip install "ragrails[url]"
```

`crawl4ai` pulls in Playwright as a package dependency. You may still need to
install browser binaries:

```bash
playwright install
```

```python
from ragrails import RagRails

rag = RagRails()

result = rag.scrape(
    url="https://example.com/about",
    mode="each",
    output_dir="files/output/web_crawled",
)

print(result.pages)
print(result.files)
print(result.errors)
```

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
    dlq_path="files/output/dlq.json",
    max_depth=3,
    max_pages=200,
)
```

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
