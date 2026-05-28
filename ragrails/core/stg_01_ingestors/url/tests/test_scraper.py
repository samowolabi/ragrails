from __future__ import annotations

import unittest

from ragrails.core.stg_01_ingestors.config import UrlIngestorConfig
from ragrails.core.stg_01_ingestors.url import scraper


class FakeCrawlResult:
    def __init__(
        self,
        *,
        success: bool,
        markdown: str = "",
        url: str = "https://example.com/docs",
        status_code: int = 200,
        metadata: dict | None = None,
        error_message: str = "",
    ) -> None:
        self.success = success
        self.markdown = markdown
        self.url = url
        self.status_code = status_code
        self.metadata = metadata or {}
        self.error_message = error_message


class FakeCrawler:
    def __init__(self, results: list[FakeCrawlResult]) -> None:
        self.results = list(results)
        self.configs = []

    async def arun(self, *, url: str, config):
        self.configs.append(config)
        return self.results.pop(0)


class UrlScraperTests(unittest.IsolatedAsyncioTestCase):
    def test_normalize_dedupes_same_url_and_config(self) -> None:
        requests, errors = scraper._normalize_url_inputs(
            [
                {
                    "url": "https://example.com/docs",
                    "mode": "each",
                    "max_depth": 1,
                    "max_pages": 1,
                },
                {
                    "url": "https://example.com/docs/",
                    "mode": "each",
                    "max_depth": 1,
                    "max_pages": 1,
                },
                {
                    "url": "https://example.com/docs",
                    "mode": "full",
                    "max_depth": 1,
                    "max_pages": 1,
                },
            ],
            default_mode="each",
            default_config=UrlIngestorConfig(),
        )

        self.assertEqual(errors, [])
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["mode"], "each")
        self.assertEqual(requests[1]["mode"], "full")

    async def test_scrape_url_returns_structured_validation_errors(self) -> None:
        result = await scraper.scrape_url(
            urls=[{"url": "ftp://example.com/docs", "mode": "each"}],
            verbose=False,
        )

        self.assertEqual(result["pages"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["outputs"], [])
        self.assertEqual(result["crawled"], [])
        self.assertEqual(result["errors"], [
            {
                "source": "ftp://example.com/docs",
                "source_kind": "url",
                "error": "url must use http:// or https://",
                "stage": "validate",
                "isRetryable": False,
            }
        ])

    async def test_crawl_one_success_returns_clean_in_memory_document(self) -> None:
        crawler = FakeCrawler([
            FakeCrawlResult(
                success=True,
                markdown="# Guide\n\nUseful documentation.",
                metadata={"title": "Guide"},
            )
        ])

        result = await scraper._crawl_one(
            crawler,
            "https://example.com/docs",
            index=1,
            max_depth=3,
            max_pages=20,
            verbose=False,
            max_retries=1,
        )

        self.assertEqual(result["pages"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["errors"] if "errors" in result else [], [])
        self.assertEqual(result["crawled"], [
            {"source": "https://example.com/docs", "id": result["outputs"][0]["id"]}
        ])

        output = result["outputs"][0]
        self.assertTrue(output["id"].startswith("url_"))
        self.assertEqual(output["display_id"], "001_docs")
        self.assertEqual(output["source"], "https://example.com/docs")
        self.assertEqual(output["title"], "Guide")
        self.assertEqual(output["text"], "# Guide\n\nUseful documentation.")
        self.assertFalse(output["text"].startswith("---"))
        self.assertEqual(output["metadata"]["source_kind"], "url")
        self.assertEqual(output["metadata"]["file_type"], "web")
        self.assertEqual(output["metadata"]["mode"], "each")
        self.assertEqual(output["metadata"]["max_depth"], 3)
        self.assertEqual(output["metadata"]["max_pages"], 20)
        self.assertGreaterEqual(output["metadata"]["elapsed_seconds"], 0)
        self.assertFalse(crawler.configs[0].verbose)

    async def test_crawl_one_retryable_failure_has_retry_input(self) -> None:
        crawler = FakeCrawler([
            FakeCrawlResult(success=False, error_message="navigation timeout"),
            FakeCrawlResult(success=False, error_message="navigation timeout"),
        ])

        result = await scraper._crawl_one(
            crawler,
            "https://example.com/docs",
            index=1,
            max_depth=3,
            max_pages=20,
            verbose=False,
            max_retries=2,
            retry_delay=0,
        )

        self.assertEqual(result["pages"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"], [
            {
                "source": "https://example.com/docs",
                "source_kind": "url",
                "error": "navigation timeout",
                "stage": "crawl",
                "isRetryable": True,
                "mode": "each",
                "attempts": 2,
                "retry_input": {
                    "url": "https://example.com/docs",
                    "mode": "each",
                    "max_depth": 3,
                    "max_pages": 20,
                },
            }
        ])

    async def test_crawl_one_empty_cleanup_failure_is_not_retryable(self) -> None:
        crawler = FakeCrawler([
            FakeCrawlResult(
                success=True,
                markdown="[Home](https://example.com)",
                metadata={"title": "Home"},
            )
        ])

        result = await scraper._crawl_one(
            crawler,
            "https://example.com",
            index=1,
            max_depth=3,
            max_pages=20,
            verbose=False,
            max_retries=3,
            retry_delay=0,
        )

        self.assertEqual(result["pages"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"], [
            {
                "source": "https://example.com",
                "source_kind": "url",
                "error": "no content returned after cleanup",
                "stage": "cleanup",
                "isRetryable": False,
                "mode": "each",
                "attempts": 3,
            }
        ])


if __name__ == "__main__":
    unittest.main()
