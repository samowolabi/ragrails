from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ragrails.interfaces.sdk.ingestion.url.client import UrlMixin
from ragrails.types import DLQ


def _make_output(slug: str = "docs") -> dict:
    return {
        "id": f"url_{slug}",
        "display_id": f"001_{slug}",
        "title": slug.capitalize(),
        "text": f"# {slug.capitalize()}\n\nContent.",
        "source": f"https://example.com/{slug}",
        "metadata": {"source_kind": "url", "file_type": "web"},
    }


def _make_error(url: str, *, retryable: bool = True) -> dict:
    error: dict = {
        "source": url,
        "source_kind": "url",
        "error": "timeout",
        "stage": "crawl",
        "isRetryable": retryable,
    }
    if retryable:
        error["retry_input"] = {"url": url, "mode": "each", "max_depth": 1, "max_pages": 1}
    return error


def _make_stats(outputs: list[dict] | None = None, failed: int = 0, errors: list[dict] | None = None) -> dict:
    outputs = outputs or [_make_output()]
    return {
        "pages": len(outputs),
        "failed": failed,
        "outputs": outputs,
        "errors": errors or [],
    }


class _Rag(UrlMixin):
    pass


class DLQTests(unittest.TestCase):

    # --- disabled (dlq=None) ---

    def test_dlq_none_by_default(self) -> None:
        stats = _make_stats()
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
            result = _Rag().scrape("https://example.com/docs")

        self.assertIsNone(result.dlq)

    # --- response mode ---

    def test_dlq_response_captures_retryable_failures(self) -> None:
        error = _make_error("https://example.com/docs")
        stats = _make_stats(outputs=[], failed=1, errors=[error])
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
            result = _Rag().scrape("https://example.com/docs", dlq=DLQ())

        self.assertIsNotNone(result.dlq)
        self.assertEqual(len(result.dlq.items), 1)
        self.assertEqual(result.dlq.items[0]["url"], "https://example.com/docs")
        self.assertIsNone(result.dlq.path)

    def test_dlq_empty_when_no_retryable_failures(self) -> None:
        stats = _make_stats()
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
            result = _Rag().scrape("https://example.com/docs", dlq=DLQ())

        self.assertIsNotNone(result.dlq)
        self.assertEqual(result.dlq.items, [])
        self.assertIsNone(result.dlq.path)

    def test_dlq_skips_non_retryable_errors(self) -> None:
        errors = [
            _make_error("https://example.com/a", retryable=True),
            _make_error("https://example.com/b", retryable=False),
        ]
        stats = _make_stats(outputs=[], failed=2, errors=errors)
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
            result = _Rag().scrape("https://example.com", dlq=DLQ())

        self.assertEqual(len(result.dlq.items), 1)
        self.assertEqual(result.dlq.items[0]["url"], "https://example.com/a")

    # --- file mode ---

    def test_dlq_saves_to_file_when_path_set(self) -> None:
        error = _make_error("https://example.com/docs")
        stats = _make_stats(outputs=[], failed=1, errors=[error])
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq_path = str(Path(tmpdir) / "dlq" / "web.json")
            with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
                result = _Rag().scrape("https://example.com/docs", dlq=DLQ(dlq_path))

            saved = json.loads(Path(dlq_path).read_text(encoding="utf-8"))
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["url"], "https://example.com/docs")
            self.assertEqual(result.dlq.path, dlq_path)

    def test_dlq_creates_parent_directories(self) -> None:
        error = _make_error("https://example.com/docs")
        stats = _make_stats(outputs=[], failed=1, errors=[error])
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq_path = str(Path(tmpdir) / "nested" / "deep" / "web.json")
            with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
                _Rag().scrape("https://example.com/docs", dlq=DLQ(dlq_path))

            self.assertTrue(Path(dlq_path).exists())

    def test_dlq_does_not_write_file_when_no_failures(self) -> None:
        stats = _make_stats()
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq_path = str(Path(tmpdir) / "web.json")
            with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
                result = _Rag().scrape("https://example.com/docs", dlq=DLQ(dlq_path))

        self.assertIsNone(result.dlq.path)
        self.assertFalse(Path(dlq_path).exists())

    # --- retry ---

    def test_retry_from_dlq_object(self) -> None:
        retry_item = {"url": "https://example.com/docs", "mode": "each", "max_depth": 1, "max_pages": 1}
        dlq = DLQ(items=[retry_item])
        stats = _make_stats()
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats) as mock_core:
            result = _Rag().scrape(dlq=dlq)

        _, kwargs = mock_core.call_args
        self.assertEqual(kwargs["urls"], [retry_item])
        self.assertEqual(result.pages, 1)

    def test_retry_from_file_string(self) -> None:
        retry_items = [{"url": "https://example.com/docs", "mode": "each", "max_depth": 1, "max_pages": 1}]
        stats = _make_stats()
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq_path = str(Path(tmpdir) / "web.json")
            Path(dlq_path).write_text(json.dumps(retry_items), encoding="utf-8")

            with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats) as mock_core:
                result = _Rag().scrape(dlq=dlq_path)

        _, kwargs = mock_core.call_args
        self.assertEqual(kwargs["urls"], retry_items)
        self.assertEqual(result.pages, 1)

    def test_retry_preserves_path_and_writes_new_failures(self) -> None:
        retry_item = {"url": "https://example.com/docs", "mode": "each", "max_depth": 1, "max_pages": 1}
        dlq = DLQ(path="files/dlq/web.json", items=[retry_item])
        error = _make_error("https://example.com/docs")
        stats = _make_stats(outputs=[], failed=1, errors=[error])
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
            with patch.object(_Rag, "_write_dlq") as mock_write:
                result = _Rag().scrape(dlq=dlq)

        mock_write.assert_called_once()
        self.assertEqual(result.dlq.path, "files/dlq/web.json")

    def test_retry_string_does_not_inherit_path(self) -> None:
        retry_items = [{"url": "https://example.com/docs", "mode": "each", "max_depth": 1, "max_pages": 1}]
        stats = _make_stats()
        with tempfile.TemporaryDirectory() as tmpdir:
            dlq_path = str(Path(tmpdir) / "web.json")
            Path(dlq_path).write_text(json.dumps(retry_items), encoding="utf-8")

            with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
                result = _Rag().scrape(dlq=dlq_path)

        self.assertIsNotNone(result.dlq)
        self.assertIsNone(result.dlq.path)

    def test_dlq_items_can_be_filtered_before_retry(self) -> None:
        errors = [
            _make_error("https://example.com/docs/a"),
            _make_error("https://example.com/blog/b"),
        ]
        stats = _make_stats(outputs=[], failed=2, errors=errors)
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
            first = _Rag().scrape("https://example.com", dlq=DLQ())

        first.dlq.items = [i for i in first.dlq.items if "docs" in i["url"]]
        self.assertEqual(len(first.dlq.items), 1)

        retry_stats = _make_stats()
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=retry_stats) as mock_core:
            _Rag().scrape(dlq=first.dlq)

        _, kwargs = mock_core.call_args
        self.assertEqual(len(kwargs["urls"]), 1)
        self.assertIn("docs", kwargs["urls"][0]["url"])

    # --- validation ---

    def test_raises_if_url_and_retry_dlq_both_given(self) -> None:
        dlq = DLQ(items=[{"url": "https://example.com", "mode": "each", "max_depth": 1, "max_pages": 1}])
        with self.assertRaises(ValueError):
            _Rag().scrape("https://example.com", dlq=dlq)

    def test_raises_if_no_url_and_no_retry_items(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().scrape(dlq=DLQ())

    def test_raises_if_dlq_file_not_found(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().scrape(dlq="nonexistent/web.json")

    def test_raises_if_dlq_file_is_not_a_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_file = str(Path(tmpdir) / "bad.json")
            Path(bad_file).write_text(json.dumps({"url": "https://example.com"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                _Rag().scrape(dlq=bad_file)


if __name__ == "__main__":
    unittest.main()
