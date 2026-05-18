# CLI Ingestion

Ingestion commands turn external sources into markdown files.

## Commands

| Command | Description |
|---|---|
| `ragrails setup-url` | Install the Playwright browser required for URL ingestion |
| `ragrails scrape` | Scrape web pages into markdown files |
| `ragrails parse` | Convert local documents into markdown files |
| `ragrails fetch` | Fetch a REST API endpoint and save responses as markdown files |

## setup-url

Run this once per environment before URL scraping:

```bash
ragrails setup-url
```

Install a specific browser:

```bash
ragrails setup-url --browser chromium
```

Options:

| Option | Default | Description |
|---|---|---|
| `--browser` | `chromium` | Playwright browser binary to install |

## scrape

Scrape one URL:

```bash
ragrails scrape https://example.com
```

Scrape multiple exact URLs:

```bash
ragrails scrape https://example.com/about https://example.com/pricing
```

Crawl a full website:

```bash
ragrails scrape https://example.com --mode full
```

Crawl with custom limits:

```bash
ragrails scrape https://example.com --mode full --max-depth 2 --max-pages 50
```

Write to a custom output folder:

```bash
ragrails scrape https://example.com --output-dir files/output/web
```

Options:

| Option | Default | Description |
|---|---|---|
| `--mode` | `each` | `each` scrapes supplied URLs. `full` crawls each URL's site |
| `--output-dir` | `files/output/web_crawled` | Folder where markdown files are written |
| `--max-depth` | `3` | Maximum crawl depth for `--mode full` |
| `--max-pages` | `200` | Maximum pages to crawl per site for `--mode full` |
| `--no-frontmatter` | - | Omit source metadata from output files |

## parse

Parse all supported files in a folder:

```bash
ragrails parse --folder files/input
```

Parse specific files:

```bash
ragrails parse --files guide.pdf --files pricing.csv --input-dir files/input
```

Write to a custom output folder:

```bash
ragrails parse --folder files/input --output-dir files/output/docs
```

Options:

| Option | Default | Description |
|---|---|---|
| `--folder` | - | Parse all supported files in this folder |
| `--files` | - | Specific file names to parse. Repeatable |
| `--input-dir` | `files/input` | Base folder used to resolve `--files` |
| `--output-dir` | `files/output/docs` | Folder where markdown files are written |
| `--no-frontmatter` | - | Omit document metadata from output files |

Supported file types:

```text
.csv, .docx, .epub, .html, .htm, .ipynb, .json, .md, .msg,
.pdf, .pptx, .rss, .tsv, .txt, .xls, .xlsx, .xml, .zip
```

## fetch

Fetch a REST API endpoint:

```bash
ragrails fetch https://api.example.com/v1/products --title "Products"
```

With headers and query parameters:

```bash
ragrails fetch https://api.example.com/v1/products \
  --header "Authorization:Bearer <token>" \
  --param limit:100
```

POST request:

```bash
ragrails fetch https://api.example.com/v1/search --method POST
```

Options:

| Option | Default | Description |
|---|---|---|
| `--title` | `API Response` | Title written into output metadata |
| `--description` | - | Description written into output metadata |
| `--method` | `GET` | HTTP method |
| `--header` | - | Request header as `KEY:VALUE`. Repeatable |
| `--param` | - | Query parameter as `KEY:VALUE`. Repeatable |
| `--output-dir` | `files/output/api` | Folder where markdown files are written |
| `--max-pages` | `100` | Maximum number of response pages to fetch |
| `--no-frontmatter` | - | Omit API metadata from output files |

Back to the [CLI overview](../README.md).
