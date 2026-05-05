"""
Run:
    uv run python -m rag.stg_01_ingestors url    # BFS-crawl a website and save as markdown
    uv run python -m rag.stg_01_ingestors api    # fetch a REST API and save as markdown
    uv run python -m rag.stg_01_ingestors docs   # convert local files (PDF, CSV, etc.) to markdown
"""

import asyncio
import sys

from .config import UrlIngestorConfig, ApiIngestorConfig, DocsIngestorConfig

mode = sys.argv[1] if len(sys.argv) > 1 else "url"

if mode == "url":
    from .url import scrape_url
    asyncio.run(scrape_url(
        # urls=["https://polar.sh/docs"],
        # urls=["https://developer.budpay.com"],
        urls=["https://opencode.ai/docs"],
        mode="full",
        config=UrlIngestorConfig(max_depth=5, max_pages=150),
    ))

elif mode == "api":
    from .api import ingest_api
    asyncio.run(ingest_api(
        url="https://api.test.com/api",
        title="Test List",
        description="List of supported banks and their codes.",
        method="GET",
        headers={"Authorization": "Bearer "},
        config=ApiIngestorConfig(),
        # pagination={
        #     "type":        "page",
        #     "param":       "page",
        #     "size_param":  "limit",
        #     "size":        50,
        #     "cursor_path": "meta.next_cursor",
        # },
    ))

elif mode == "docs":
    from .docs import ingest_docs
    ingest_docs(
        docs=[
            {
                "filename":    "sam-owolabi.pdf",
                "title":       "Sam Owolabi CV",
                "description": "A sample document for ingestion.",
            },
            {
                "filename":    "titanic.csv",
                "title":       "Titanic Dataset",
                "description": "Dataset containing information about Titanic passengers."
            }
        ],
        config=DocsIngestorConfig(),
    )

else:
    print(f"Unknown mode '{mode}'. Use: url | api | docs")
    sys.exit(1)
