# CLI

The Ragrails CLI lets you run ingestion commands directly from the terminal without writing Python.

## Install

```bash
pip install ragrails
```

The `ragrails` command is available immediately after install. No extra setup needed.

Verify:

```bash
ragrails --help
```

## Commands

| Command | Description |
|---|---|
| `ragrails setup-url` | Install the Playwright browser required for URL ingestion |
| `ragrails scrape` | Scrape web pages into markdown files |
| `ragrails parse` | Convert local documents into markdown files |
| `ragrails fetch` | Fetch a REST API endpoint and save responses as markdown files |

---

## setup-url

Install the Playwright browser required for URL ingestion. Run this once per environment before using `scrape`.

```bash
ragrails setup-url
```

This installs Chromium by default. To install a different browser:

```bash
ragrails setup-url --browser chromium
```

### Options

| Option | Default | Description |
|---|---|---|
| `--browser` | `chromium` | Playwright browser binary to install. |

---

## scrape

Scrape one or more URLs into markdown files.

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

Crawl with custom depth and page limits:

```bash
ragrails scrape https://example.com --mode full --max-depth 2 --max-pages 50
```

Write to a custom output folder:

```bash
ragrails scrape https://example.com --output-dir my/output/folder
```

Omit frontmatter metadata:

```bash
ragrails scrape https://example.com --no-frontmatter
```

### Options

| Option | Default | Description |
|---|---|---|
| `--mode` | `each` | `each` scrapes only the supplied URLs. `full` crawls each URL's site. |
| `--output-dir` | `files/output/web_crawled` | Folder where markdown files are written. |
| `--max-depth` | `3` | Maximum crawl depth for `--mode full`. |
| `--max-pages` | `200` | Maximum pages to crawl per site for `--mode full`. |
| `--no-frontmatter` | — | Omit source metadata from output files. |

---

## parse

Convert local documents into markdown files.

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
ragrails parse --folder files/input --output-dir my/output/folder
```

Omit frontmatter metadata:

```bash
ragrails parse --folder files/input --no-frontmatter
```

### Options

| Option | Default | Description |
|---|---|---|
| `--folder` | — | Parse all supported files in this folder. |
| `--files` | — | Specific file names to parse. Repeatable. |
| `--input-dir` | `files/input` | Base folder used to resolve `--files`. |
| `--output-dir` | `files/output/docs` | Folder where markdown files are written. |
| `--no-frontmatter` | — | Omit document metadata from output files. |

Supported file types:

```text
.csv, .docx, .epub, .html, .htm, .ipynb, .json, .md, .msg,
.pdf, .pptx, .rss, .tsv, .txt, .xls, .xlsx, .xml, .zip
```

---

## fetch

Fetch a REST API endpoint and save each response page as a markdown file.

Basic GET request:

```bash
ragrails fetch https://api.example.com/v1/products --title "Products"
```

With a single header:

```bash
ragrails fetch https://api.example.com/v1/products \
  --header "Authorization:Bearer <token>"
```

With multiple headers:

```bash
ragrails fetch https://api.example.com/v1/products \
  --header "Authorization:Bearer <token>" \
  --header "X-Api-Key:my-key"
```

With query parameters:

```bash
ragrails fetch https://api.example.com/v1/products \
  --param limit:100 \
  --param status:active
```

POST request:

```bash
ragrails fetch https://api.example.com/v1/search --method POST
```

Limit pages fetched:

```bash
ragrails fetch https://api.example.com/v1/products --max-pages 5
```

### Options

| Option | Default | Description |
|---|---|---|
| `--title` | `API Response` | Title written into output metadata. |
| `--description` | — | Description written into output metadata. |
| `--method` | `GET` | HTTP method. One of `GET`, `POST`, `PUT`, `PATCH`, `DELETE`. |
| `--header` | — | Request header as `KEY:VALUE`. Repeatable. |
| `--param` | — | Query parameter as `KEY:VALUE`. Repeatable. |
| `--output-dir` | `files/output/api` | Folder where markdown files are written. |
| `--max-pages` | `100` | Maximum number of response pages to fetch. |
| `--no-frontmatter` | — | Omit API metadata from output files. |

---

## Global options

These options are available on every command.

```bash
ragrails --version
ragrails --help
ragrails scrape --help
ragrails parse --help
ragrails fetch --help
```
