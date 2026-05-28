from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ragrails.interfaces.sdk.ingestion.url.client import UrlMixin


def _make_output(slug: str = "docs") -> dict:
    return {
        "id": f"url_{slug}",
        "display_id": f"001_{slug}",
        "title": slug.capitalize(),
        "text": f"# {slug.capitalize()}\n\nContent.",
        "source": f"https://example.com/{slug}",
        "metadata": {"source_kind": "url", "file_type": "web"},
    }


def _make_stats(outputs: list[dict] | None = None, failed: int = 0) -> dict:
    outputs = outputs or [_make_output()]
    return {
        "pages": len(outputs),
        "failed": failed,
        "outputs": outputs,
        "errors": [],
    }


class _Rag(UrlMixin):
    pass


class UrlSDKTests(unittest.TestCase):

    # --- setup_url ---

    def test_setup_url_rejects_empty_browser(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().setup_url(browser="  ")

    def test_setup_url_runs_playwright_install_and_returns_output(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="installed",
            stderr="",
        )

        with patch.dict("sys.modules", {"playwright": object()}):
            with patch("subprocess.run", return_value=completed) as run:
                result = _Rag().setup_url(browser="firefox")

        expected_command = [sys.executable, "-m", "playwright", "install", "firefox"]
        run.assert_called_once_with(
            expected_command,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result["browser"], "firefox")
        self.assertEqual(result["command"], expected_command)
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(result["stdout"], "installed")
        self.assertEqual(result["stderr"], "")

    def test_setup_url_failure_includes_stdout_and_stderr(self) -> None:
        completed = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="download started",
            stderr="network failed",
        )

        with patch.dict("sys.modules", {"playwright": object()}):
            with patch("subprocess.run", return_value=completed):
                with self.assertRaises(RuntimeError) as ctx:
                    _Rag().setup_url(browser="chromium")

        message = str(ctx.exception)
        self.assertIn("Failed to install Playwright browser binary", message)
        self.assertIn("python", message)
        self.assertIn("stderr: network failed", message)
        self.assertIn("stdout: download started", message)

    # --- validation ---

    def test_raises_on_invalid_mode(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().scrape("https://example.com", mode="crawl")

    def test_raises_if_max_pages_less_than_one(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().scrape("https://example.com", max_pages=0)

    def test_raises_if_max_depth_negative(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().scrape("https://example.com", max_depth=-1)

    def test_raises_on_invalid_url_scheme(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().scrape("ftp://example.com")

    def test_raises_on_empty_url_string(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().scrape("   ")

    def test_raises_on_empty_url_list(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().scrape([])

    def test_raises_if_dict_item_missing_url_key(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().scrape([{"mode": "full"}])

    def test_raises_on_invalid_output_format(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().scrape("https://example.com", output_format="xml")

    def test_raises_on_invalid_output_dest(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().scrape("https://example.com", output_dest="print")

    def test_raises_if_output_dest_file_without_output_dir(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().scrape("https://example.com", output_dest="file")

    # --- scrape response ---

    def test_scrape_single_url_returns_scrape_result(self) -> None:
        stats = _make_stats()
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
            result = _Rag().scrape("https://example.com/docs")

        self.assertEqual(result.pages, 1)
        self.assertEqual(result.failed, 0)
        self.assertEqual(len(result.outputs), 1)
        self.assertNotIn("output_path", result.outputs[0])
        self.assertEqual(result.errors, [])

    def test_scrape_list_of_urls_returns_combined_result(self) -> None:
        stats = _make_stats(outputs=[_make_output("docs"), _make_output("blog")])
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
            result = _Rag().scrape(["https://example.com/docs", "https://example.com/blog"])

        self.assertEqual(result.pages, 2)

    def test_scrape_passes_mode_and_config_to_core(self) -> None:
        stats = _make_stats()
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats) as mock_core:
            _Rag().scrape("https://example.com", mode="full", max_depth=2, max_pages=50)

        _, kwargs = mock_core.call_args
        self.assertEqual(kwargs["mode"], "full")
        self.assertEqual(kwargs["config"].max_depth, 2)
        self.assertEqual(kwargs["config"].max_pages, 50)

    def test_scrape_per_url_dict_passes_through_to_core(self) -> None:
        stats = _make_stats()
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats) as mock_core:
            _Rag().scrape([
                "https://example.com/docs",
                {"url": "https://example.com/blog", "mode": "full", "max_depth": 2},
            ])

        _, kwargs = mock_core.call_args
        urls_arg = kwargs["urls"]
        self.assertEqual(len(urls_arg), 2)
        self.assertIsInstance(urls_arg[1], dict)

    def test_scrape_markdown_format_includes_text_in_output(self) -> None:
        stats = _make_stats()
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
            result = _Rag().scrape("https://example.com/docs", output_format="markdown")

        self.assertIn("text", result.outputs[0])

    def test_scrape_json_format_includes_full_output_dict(self) -> None:
        stats = _make_stats(outputs=[_make_output()])
        with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
            result = _Rag().scrape("https://example.com/docs", output_format="json")

        self.assertIn("metadata", result.outputs[0])
        self.assertIn("source", result.outputs[0])

    # --- file output ---

    def test_scrape_saves_markdown_file_to_output_dir(self) -> None:
        output = _make_output()
        stats = _make_stats(outputs=[output])
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
                result = _Rag().scrape(
                    "https://example.com/docs",
                    output_format="markdown",
                    output_dest="file",
                    output_dir=tmpdir,
                )

            saved_path = Path(result.outputs[0]["output_path"])
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.suffix, ".md")
            self.assertEqual(saved_path.read_text(encoding="utf-8"), output["text"])

    def test_scrape_saves_json_file_to_output_dir(self) -> None:
        output = _make_output()
        stats = _make_stats(outputs=[output])
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
                result = _Rag().scrape(
                    "https://example.com/docs",
                    output_format="json",
                    output_dest="file",
                    output_dir=tmpdir,
                )

            saved_path = Path(result.outputs[0]["output_path"])
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.suffix, ".json")
            saved = json.loads(saved_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["id"], output["id"])

    def test_scrape_adds_output_path_to_every_output(self) -> None:
        stats = _make_stats(outputs=[_make_output("docs"), _make_output("blog")])
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("ragrails.core.stg_01_ingestors.url.scrape_url", return_value=stats):
                result = _Rag().scrape(
                    ["https://example.com/docs", "https://example.com/blog"],
                    output_dest="file",
                    output_dir=tmpdir,
                )

        for item in result.outputs:
            self.assertIn("output_path", item)


if __name__ == "__main__":
    unittest.main()
