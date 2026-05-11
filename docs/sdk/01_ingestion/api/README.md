# API Ingestion

Use `RagRails().fetch()` to fetch REST API responses and save each response
page as markdown.

## Install

```bash
pip install "ragrails[api]"
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
