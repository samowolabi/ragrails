from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from ragrails.interfaces.server.app import create_app


class ServerIngestionRouteTests(unittest.TestCase):
    def test_url_stream_returns_sse_events(self) -> None:
        client = TestClient(create_app())
        events = [
            {"type": "progress", "stage": "scrape", "message": "Started", "data": {}, "sequence": 1},
            {"type": "final", "stage": "complete", "message": "Done", "data": {"pages": 1}, "sequence": 2},
        ]

        with patch("ragrails.interfaces.server.ingestion.services.scrape_url_stream", return_value=iter(events)):
            response = client.post("/v1/ingest/url/stream", json={"url": "https://example.com"})

        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertIn("event: progress", response.text)
        self.assertIn("event: final", response.text)

    def test_upload_docs_accepts_multipart_formdata(self) -> None:
        client = TestClient(create_app())
        expected = {
            "documents": 1,
            "failed": 0,
            "outputs": [{"text": "# Guide"}],
            "errors": [],
        }

        with patch("ragrails.interfaces.server.ingestion.services.parse_uploaded_docs", return_value=expected) as parse:
            response = client.post(
                "/v1/ingest/docs/upload",
                data={
                    "frontmatter": "true",
                    "title": "Guide",
                    "description": "Uploaded guide",
                },
                files={
                    "files": ("guide.md", b"# Guide\n", "text/markdown"),
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), expected)
        parse.assert_called_once()
        uploaded = parse.call_args.args[0]
        self.assertEqual(parse.call_args.kwargs["frontmatter"], True)
        self.assertEqual(uploaded[0]["content"], b"# Guide\n")
        self.assertEqual(uploaded[0]["filename"], "guide.md")
        self.assertEqual(uploaded[0]["title"], "Guide")
        self.assertEqual(uploaded[0]["description"], "Uploaded guide")
        self.assertEqual(uploaded[0]["content_type"], "text/markdown")


if __name__ == "__main__":
    unittest.main()
