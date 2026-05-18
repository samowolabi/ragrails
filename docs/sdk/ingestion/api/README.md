# API Ingestion

Use `RagRails().fetch()` to fetch REST API responses and save each response
page as markdown.

## Install

```bash
pip install ragrails
```

```python
from ragrails import RagRails

result = RagRails().fetch(
    url="https://api.example.com/v1/products",
    title="Products",
    description="Product catalog from the public API.",
    output_dir="files/output/api",
)

print(result.pages)
print(result.items)
print(result.files)
print(result.errors)
```

## CLI

You can run the same API ingestion flow from the terminal with `ragrails fetch`.

```bash
ragrails fetch https://api.example.com/v1/products --title "Products"
```

Pass headers and query parameters with repeatable options:

```bash
ragrails fetch https://api.example.com/v1/products \
  --header "Authorization:Bearer <token>" \
  --param limit:100
```

See the full [CLI reference](../../../cli/README.md#fetch).

## Request Options

Pass headers, query parameters, and request bodies when needed.

```python
from ragrails import RagRails

result = RagRails().fetch(
    url="https://api.example.com/v1/products",
    method="GET",
    headers={"Authorization": "Bearer <token>"},
    params={"limit": 100},
    title="Products",
    description="Product catalog from the API.",
)
```

For `POST`, `PUT`, or `PATCH` endpoints, pass `body`.

```python
result = RagRails().fetch(
    url="https://api.example.com/v1/search",
    method="POST",
    headers={"Authorization": "Bearer <token>"},
    body={"query": "payments"},
    title="Search Results",
)
```

## Pagination

Pass a pagination config when the API returns multiple pages.

```python
result = RagRails().fetch(
    url="https://api.example.com/v1/products",
    title="Products",
    pagination={
        "type": "page",
        "param": "page",
        "size_param": "limit",
        "size": 100,
    },
    max_pages=20,
)
```

## Output

API ingestion writes markdown files to `output_dir`.

```text
files/output/api/
  001_api_example_com_v1_products.md
  002_api_example_com_v1_products.md
```

Each file contains the API response converted from JSON to markdown.

## Frontmatter

Frontmatter is enabled by default.

```python
result = RagRails().fetch(
    url="https://api.example.com/v1/products",
    frontmatter=True,
)
```

Disable it when you want only the converted markdown body.

```python
result = RagRails().fetch(
    url="https://api.example.com/v1/products",
    frontmatter=False,
)
```

## Function

```python
RagRails().fetch(
    url,
    *,
    title="API Response",
    description="",
    method="GET",
    headers=None,
    params=None,
    body=None,
    pagination=None,
    max_pages=100,
    output_dir="files/output/api",
    frontmatter=True,
)
```

### `fetch()` Parameters

| Parameter | Type | Default | Required | Description |
|---|---|---:|---|---|
| `url` | `str` | - | Yes | Absolute `http` or `https` API endpoint. |
| `title` | `str` | `"API Response"` | No | Title written into output metadata. |
| `description` | `str` | `""` | No | Description written into output metadata. |
| `method` | `str` | `"GET"` | No | HTTP method. Supports `GET`, `POST`, `PUT`, `PATCH`, and `DELETE`. |
| `headers` | `dict \| None` | `None` | No | Request headers, for example authorization headers. |
| `params` | `dict \| None` | `None` | No | Query string parameters. |
| `body` | `dict \| None` | `None` | No | JSON request body for methods such as `POST` or `PATCH`. |
| `pagination` | `dict \| None` | `None` | No | Pagination configuration for multi-page APIs. |
| `max_pages` | `int` | `100` | No | Maximum number of response pages to fetch. |
| `output_dir` | `str` | `"files/output/api"` | No | Folder where markdown files are written. |
| `frontmatter` | `bool` | `True` | No | Adds API metadata to the top of each markdown file. |

## Result

`fetch()` returns an `ApiIngestResult`:

```python
print(result.pages)
print(result.items)
print(result.failed)
print(result.output_dir)
print(result.files)
print(result.errors)
```

## Validation

`fetch()` validates inputs before making the request.

It raises `ValueError` when:

- `url` is empty.
- `url` is not an absolute `http` or `https` URL.
- `method` is not `GET`, `POST`, `PUT`, `PATCH`, or `DELETE`.
- `output_dir` is empty.
- `max_pages` is less than `1`.
- `headers`, `params`, `body`, or `pagination` are not dictionaries when provided.

```python
from ragrails import RagRails

RagRails().fetch(
    url="api.example.com/products",
)
# ValueError: Invalid URL 'api.example.com/products' — use an absolute http(s) URL
```

## Error Handling

Request, conversion, and write failures are recorded in the returned result.

```python
result = RagRails().fetch(
    url="https://api.example.com/v1/products",
)

if result.failed:
    print(result.errors)
```
