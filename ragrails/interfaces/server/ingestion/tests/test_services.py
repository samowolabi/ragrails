from __future__ import annotations

import unittest
from unittest.mock import patch

from ragrails.interfaces.server.ingestion.schemas import ApiIngestRequest, DocsIngestRequest, UrlIngestRequest
from ragrails.interfaces.server.ingestion.services import fetch_api, parse_docs, scrape_url
from ragrails.interfaces.sdk import RagRails
from ragrails.types import ApiIngestResult, ParseResult, ScrapeResult


class ServerIngestionServiceTests(unittest.TestCase):
    def test_fetch_api_calls_sdk(self) -> None:
        expected = ApiIngestResult(documents=1, failed=0, outputs=[{"text": "ok"}], errors=[])

        with patch.object(RagRails, "fetch", return_value=expected) as fetch:
            result = fetch_api(ApiIngestRequest(url="https://api.example.com/posts", params={"limit": 1}))

        fetch.assert_called_once()
        self.assertEqual(fetch.call_args.kwargs["url"], "https://api.example.com/posts")
        self.assertEqual(fetch.call_args.kwargs["params"], {"limit": 1})
        self.assertEqual(result["documents"], 1)
        self.assertEqual(result["outputs"], [{"text": "ok"}])

    def test_scrape_url_calls_sdk(self) -> None:
        expected = ScrapeResult(pages=1, failed=0, outputs=[{"text": "ok"}], errors=[])

        with patch.object(RagRails, "scrape", return_value=expected) as scrape:
            result = scrape_url(UrlIngestRequest(url=["https://example.com"], mode="each"))

        scrape.assert_called_once()
        self.assertEqual(scrape.call_args.kwargs["url"], ["https://example.com"])
        self.assertEqual(result["pages"], 1)

    def test_parse_docs_normalizes_document_inputs(self) -> None:
        expected = ParseResult(documents=1, failed=0, outputs=[{"text": "ok"}], errors=[])

        with patch.object(RagRails, "parse", return_value=expected) as parse:
            result = parse_docs(DocsIngestRequest(files=[{"path": "docs/guide.md", "title": "Guide"}]))

        parse.assert_called_once()
        self.assertEqual(parse.call_args.kwargs["files"], [{"path": "docs/guide.md", "content": None, "filename": None, "title": "Guide", "description": None}])
        self.assertEqual(result["documents"], 1)


if __name__ == "__main__":
    unittest.main()
