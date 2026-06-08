# CLI Ingestion

Commands for getting external content into SDK ingestion result shapes.

## Commands

| Command | SDK method | Purpose |
|---|---|---|
| `setup-url` | `RagRails().setup_url()` | Install the browser binary needed by URL ingestion. |
| `scrape` | `RagRails().scrape()` | Scrape one or more URLs into markdown documents. |
| `parse` | `RagRails().parse()` | Parse local documents into markdown documents. |
| `fetch` | `RagRails().fetch()` | Fetch REST API responses into markdown documents. |

## Examples

```bash
ragrails setup-url
```

For automation:

```bash
ragrails setup-url --browser chromium
```

Show the underlying Playwright install command:

```bash
ragrails setup-url --browser chromium --verbose
```

```bash
ragrails scrape https://example.com/docs --mode full --max-pages 10
```

```bash
ragrails parse --files docs/report.pdf --output-dir files/output/docs
```

```bash
ragrails fetch https://api.example.com/posts --header "Authorization:Bearer token"
```

When `--output-dir` is omitted, ingestion commands return summary output only
and keep the SDK response in memory.
