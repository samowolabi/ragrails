from __future__ import annotations

import asyncio
import json

from ragrails.core.stg_01_ingestors.url.scraper import scrape_url


def main() -> None:
    result = asyncio.run(
        scrape_url(
            urls=[
                {
                    "url": "https://developer.budpay.com",
                    "mode": "each",
                },
                {
                    "url": "https://developer.budpay.com",
                    "mode": "full",
                    "max_depth": 1,
                    "max_pages": 5,
                },
            ],
            verbose=True,
        )
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
