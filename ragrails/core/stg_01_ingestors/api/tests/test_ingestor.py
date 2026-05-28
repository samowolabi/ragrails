from __future__ import annotations

import unittest
from unittest.mock import patch

from ragrails.core.stg_01_ingestors.api import ingestor
from ragrails.core.stg_01_ingestors.config import ApiIngestorConfig


async def fake_fetch_pages_success(**kwargs):
    yield 1, {"items": [{"id": 1}, {"id": 2}]}
    yield 2, {"items": [{"id": 3}]}


async def fake_fetch_pages_failure(**kwargs):
    raise TimeoutError("request timed out")
    yield


class ApiIngestorTests(unittest.IsolatedAsyncioTestCase):
    async def test_ingest_single_api_success_returns_clean_documents(self) -> None:
        with (
            patch.object(ingestor, "fetch_pages", side_effect=fake_fetch_pages_success),
            patch.object(ingestor, "_json_to_md", side_effect=lambda data, title: f"# {title}\n\npayload"),
        ):
            result = await ingestor.ingest_api(
                url="https://api.example.com/products",
                title="Products",
                description="Product catalog",
                max_pages=2,
                timeout=12.5,
            )

        self.assertEqual(result["documents"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["errors"], [])

        first = result["outputs"][0]
        self.assertTrue(first["id"].startswith("api_"))
        self.assertEqual(first["display_id"], "001_api_example_com_products")
        self.assertEqual(first["source"], "https://api.example.com/products")
        self.assertEqual(first["title"], "Products — page 1")
        self.assertEqual(first["text"], "# Products — page 1\n\npayload")
        self.assertFalse(first["text"].startswith("---"))
        self.assertEqual(first["metadata"]["source_kind"], "api")
        self.assertEqual(first["metadata"]["file_type"], "api")
        self.assertEqual(first["metadata"]["description"], "Product catalog")
        self.assertEqual(first["metadata"]["method"], "GET")
        self.assertEqual(first["metadata"]["page"], 1)
        self.assertEqual(first["metadata"]["item_count"], 2)
        self.assertEqual(first["metadata"]["max_pages"], 2)
        self.assertEqual(first["metadata"]["timeout"], 12.5)
        self.assertGreaterEqual(first["metadata"]["elapsed_seconds"], 0)

    async def test_ingest_api_array_supports_per_entry_config(self) -> None:
        calls = []

        async def fake_fetch_pages(**kwargs):
            calls.append(kwargs)
            yield 1, [{"id": 1}]

        with (
            patch.object(ingestor, "fetch_pages", side_effect=fake_fetch_pages),
            patch.object(ingestor, "_json_to_md", return_value="# Response"),
        ):
            result = await ingestor.ingest_api(
                apis=[
                    {
                        "url": "https://api.example.com/products",
                        "title": "Products",
                        "method": "POST",
                        "body": {"active": True},
                        "max_pages": 3,
                        "timeout": 5,
                    },
                    "https://api.example.com/users",
                ],
                config=ApiIngestorConfig(max_pages=8, timeout=30),
            )

        self.assertEqual(result["documents"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(calls[0]["method"], "POST")
        self.assertEqual(calls[0]["body"], {"active": True})
        self.assertEqual(calls[0]["max_pages"], 3)
        self.assertEqual(calls[0]["timeout"], 5)
        self.assertEqual(calls[1]["url"], "https://api.example.com/users")
        self.assertEqual(calls[1]["method"], "GET")
        self.assertEqual(calls[1]["max_pages"], 8)
        self.assertEqual(calls[1]["timeout"], 30)

    async def test_validation_error_uses_standard_shape(self) -> None:
        result = await ingestor.ingest_api(
            apis=[{"url": "ftp://api.example.com/products", "title": "Products"}],
        )

        self.assertEqual(result["documents"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["outputs"], [])
        self.assertEqual(result["errors"], [
            {
                "source": "ftp://api.example.com/products",
                "source_kind": "api",
                "stage": "validate",
                "error": "url must use http:// or https://",
                "isRetryable": False,
                "attempts": 1,
            }
        ])

    async def test_request_error_is_retryable_and_has_retry_input(self) -> None:
        with patch.object(ingestor, "fetch_pages", side_effect=fake_fetch_pages_failure):
            result = await ingestor.ingest_api(
                url="https://api.example.com/products",
                title="Products",
                description="Product catalog",
                max_pages=2,
                timeout=5,
            )

        self.assertEqual(result["documents"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"], [
            {
                "source": "https://api.example.com/products",
                "source_kind": "api",
                "stage": "request",
                "error": "request timed out",
                "isRetryable": True,
                "attempts": 1,
                "retry_input": {
                    "url": "https://api.example.com/products",
                    "title": "Products",
                    "description": "Product catalog",
                    "method": "GET",
                    "max_pages": 2,
                    "timeout": 5,
                },
            }
        ])

    async def test_bad_max_pages_does_not_fall_back_to_config(self) -> None:
        result = await ingestor.ingest_api(
            url="https://api.example.com/products",
            title="Products",
            max_pages=0,
        )

        self.assertEqual(result["documents"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"][0]["stage"], "validate")
        self.assertEqual(result["errors"][0]["error"], "max_pages must be a positive integer")


if __name__ == "__main__":
    unittest.main()
