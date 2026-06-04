from __future__ import annotations

import unittest
from unittest.mock import patch

from click.testing import CliRunner

from ragrails.interfaces.cli.main import cli
from ragrails.interfaces.sdk import RagRails
from ragrails.types import ApiIngestResult, ParseResult, ScrapeResult


class CliIngestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def invoke(self, args: list[str]):
        return self.runner.invoke(cli, args)

    def test_scrape_parses_multiple_urls_and_options(self) -> None:
        expected = ScrapeResult(pages=2, failed=0, outputs=[], errors=[])

        with patch.object(RagRails, "scrape", return_value=expected) as scrape:
            result = self.invoke([
                "scrape",
                "https://example.com/a",
                "https://example.com/b",
                "--mode",
                "full",
                "--max-depth",
                "2",
                "--max-pages",
                "10",
            ])

        self.assertEqual(result.exit_code, 0, result.output)
        scrape.assert_called_once_with(
            url=["https://example.com/a", "https://example.com/b"],
            mode="full",
            frontmatter=False,
            max_depth=2,
            max_pages=10,
            output_format="markdown",
            output_dest="response",
            output_dir=None,
        )
        self.assertIn("Pages scraped : 2", result.output)

    def test_parse_requires_folder_or_files(self) -> None:
        result = self.invoke(["parse"])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Provide --folder or at least one --files value", result.output)

    def test_parse_rejects_folder_and_files_together(self) -> None:
        result = self.invoke(["parse", "--folder", "files/input", "--files", "guide.pdf"])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Use --folder or --files, not both", result.output)

    def test_parse_passes_file_options_to_sdk(self) -> None:
        expected = ParseResult(documents=2, failed=0, outputs=[], errors=[])

        with patch.object(RagRails, "parse", return_value=expected) as parse:
            result = self.invoke(["parse", "--files", "guide.pdf", "--files", "pricing.csv"])

        self.assertEqual(result.exit_code, 0, result.output)
        parse.assert_called_once_with(
            files=["guide.pdf", "pricing.csv"],
            folder=None,
            frontmatter=False,
            output_format="markdown",
            output_dest="response",
            output_dir=None,
        )
        self.assertIn("Documents parsed : 2", result.output)

    def test_fetch_parses_headers_params_and_method(self) -> None:
        expected = ApiIngestResult(documents=1, failed=0, outputs=[], errors=[])

        with patch.object(RagRails, "fetch", return_value=expected) as fetch:
            result = self.invoke([
                "fetch",
                "https://api.example.com/products",
                "--title",
                "Products",
                "--description",
                "Product catalog",
                "--method",
                "POST",
                "--header",
                "Authorization:Bearer token",
                "--param",
                "limit:100",
                "--max-pages",
                "5",
            ])

        self.assertEqual(result.exit_code, 0, result.output)
        fetch.assert_called_once_with(
            url="https://api.example.com/products",
            title="Products",
            description="Product catalog",
            method="POST",
            headers={"Authorization": "Bearer token"},
            params={"limit": "100"},
            max_pages=5,
            frontmatter=False,
            output_format="markdown",
            output_dest="response",
            output_dir=None,
        )
        self.assertIn("Documents fetched : 1", result.output)

    def test_fetch_rejects_bad_header_pair(self) -> None:
        result = self.invoke(["fetch", "https://api.example.com/products", "--header", "Authorization"])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Expected KEY:VALUE", result.output)


if __name__ == "__main__":
    unittest.main()
