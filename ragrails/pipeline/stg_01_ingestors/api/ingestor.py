"""
API ingestor — fetches paginated REST API responses and saves each page
as a markdown file with frontmatter metadata.
"""

import io
import json
import os
import re
import time

from markitdown import MarkItDown
from ragrails.tools.api_client import fetch_pages, extract_items
from ragrails.utils.frontmatter import build as build_frontmatter
from ragrails.utils.report import print_report
from ..config import ApiIngestorConfig

_md = MarkItDown()


def _json_to_md(data: dict | list, title: str = "") -> str:
    stream = io.BytesIO(json.dumps(data, indent=2).encode())
    content = _md.convert_stream(stream, file_extension=".json").text_content
    return f"# {title}\n\n{content}" if title else content


def _slug(url: str) -> str:
    return re.sub(r"[^\w]", "_", url.split("//")[-1].strip("/"))


async def ingest_api(
    url: str,
    title: str,
    description: str,
    method: str = "GET",
    headers: dict | None = None,
    params: dict | None = None,
    body: dict | None = None,
    pagination: dict | None = None,
    max_pages: int = 100,
    config: ApiIngestorConfig | None = None,
    frontmatter: bool = True,
) -> dict:
    """Fetch all pages from a REST API and save each as a markdown file.

    Args:
        url:        API endpoint URL.
        title:      Human-readable name for this dataset.
        description: Short description for frontmatter.
        method:     HTTP method (default GET).
        headers:    Request headers (e.g. Authorization).
        params:     Base query parameters.
        body:       Request body for POST/PUT/PATCH.
        pagination: Pagination config — see ragrails/tools/api_client.py for keys.
        max_pages:  Hard cap on pages to fetch.
        config:     ApiIngestorConfig for output path and request settings.
    """
    cfg = config or ApiIngestorConfig()
    output_dir = cfg.output_dir
    os.makedirs(output_dir, exist_ok=True)

    start = time.time()
    stats = {"pages": 0, "items": 0, "failed": 0, "page_times": [], "files": [], "errors": []}

    try:
        async for page_num, data in fetch_pages(
            url=url,
            method=method,
            headers=headers,
            params=params,
            body=body,
            pagination=pagination,
            max_pages=max_pages,
        ):
            t0 = time.time()
            slug = _slug(url)
            filename = os.path.join(output_dir, f"{page_num:03d}_{slug}.md")

            metadata = ""
            if frontmatter:
                metadata = build_frontmatter(
                    path=url,
                    title=f"{title} — page {page_num}",
                    description=description,
                    original_type="api",
                )
            try:
                content = metadata + _json_to_md(data, title=f"{title} — page {page_num}")
                with open(filename, "w") as f:
                    f.write(content)
            except Exception as e:
                message = f"{filename}: {e}"
                print(f"  [page-{page_num}] failed: {message}")
                stats["failed"] += 1
                stats["errors"].append(message)
                continue

            elapsed_page = time.time() - t0
            item_count = len(extract_items(data)) or 1
            stats["pages"] += 1
            stats["items"] += item_count
            stats["page_times"].append(elapsed_page)
            stats["files"].append(filename)
            print(f"  [page-{page_num}] → {filename}  ({item_count} items, {elapsed_page:.2f}s)")

    except Exception as e:
        message = f"{url}: {e}"
        print(f"  failed: {message}")
        stats["failed"] += 1
        stats["errors"].append(message)

    elapsed = time.time() - start
    avg = sum(stats["page_times"]) / len(stats["page_times"]) if stats["page_times"] else 0

    print_report(
        "API INGEST REPORT",
        {
            "URL":           url,
            "Total time":    f"{elapsed:.2f}s",
            "Pages fetched": stats["pages"],
            "Total items":   stats["items"],
            "Avg time/page": f"{avg:.2f}s",
            "Failed":        stats["failed"],
        },
    )
    return stats
