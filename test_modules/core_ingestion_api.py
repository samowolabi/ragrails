from __future__ import annotations

import asyncio
import json

from ragrails.core.stg_01_ingestors.api.ingestor import ingest_api


def main() -> None:
    result = asyncio.run(
        ingest_api(
            apis=[
                {
                    "url": "https://jsonplaceholder.typicode.com/posts",
                    "title": "JSONPlaceholder Posts",
                    "description": "A collection of posts from JSONPlaceholder API",
                    "max_pages": 1,
                }
            ],
        )
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
