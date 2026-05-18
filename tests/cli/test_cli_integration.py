from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from ragrails.types import (
    ApiIngestResult,
    EmbedResult,
    ParseResult,
    RetrievedChunk,
    RetrieveResult,
    ScrapeResult,
    StoreResult,
)
from ragrails.usage.cli.main import cli
from ragrails.usage.sdk import RagRails


class CliIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def invoke(self, args: list[str]):
        return self.runner.invoke(cli, args)

    def test_root_help_lists_stage_commands(self) -> None:
        result = self.invoke(["--help"])

        self.assertEqual(result.exit_code, 0, result.output)
        for command in [
            "setup-url",
            "scrape",
            "parse",
            "fetch",
            "chunk",
            "chunk-file",
            "embed",
            "store",
            "retrieve",
        ]:
            self.assertIn(command, result.output)

    def test_scrape_parses_multiple_urls_and_options(self) -> None:
        expected = ScrapeResult(
            pages=2,
            failed=0,
            output_dir="out/web",
            files=["out/web/a.md", "out/web/b.md"],
            dlq_path="out/web/dlq.json",
            errors=[],
        )

        with patch.object(RagRails, "scrape", return_value=expected) as scrape:
            result = self.invoke([
                "scrape",
                "https://example.com/a",
                "https://example.com/b",
                "--mode",
                "full",
                "--output-dir",
                "out/web",
                "--max-depth",
                "2",
                "--max-pages",
                "10",
                "--no-frontmatter",
            ])

        self.assertEqual(result.exit_code, 0, result.output)
        scrape.assert_called_once_with(
            url=["https://example.com/a", "https://example.com/b"],
            mode="full",
            output_dir="out/web",
            frontmatter=False,
            max_depth=2,
            max_pages=10,
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
        expected = ParseResult(
            documents=2,
            failed=0,
            output_dir="out/docs",
            files=["out/docs/guide.md", "out/docs/pricing.md"],
            errors=[],
        )

        with patch.object(RagRails, "parse", return_value=expected) as parse:
            result = self.invoke([
                "parse",
                "--files",
                "guide.pdf",
                "--files",
                "pricing.csv",
                "--input-dir",
                "files/input",
                "--output-dir",
                "out/docs",
                "--no-frontmatter",
            ])

        self.assertEqual(result.exit_code, 0, result.output)
        parse.assert_called_once_with(
            files=["guide.pdf", "pricing.csv"],
            folder=None,
            input_dir="files/input",
            output_dir="out/docs",
            frontmatter=False,
        )
        self.assertIn("Documents parsed : 2", result.output)

    def test_fetch_parses_headers_params_and_method(self) -> None:
        expected = ApiIngestResult(
            pages=1,
            items=3,
            failed=0,
            output_dir="out/api",
            files=["out/api/products.md"],
            errors=[],
        )

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
                "--output-dir",
                "out/api",
                "--max-pages",
                "5",
                "--no-frontmatter",
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
            output_dir="out/api",
            frontmatter=False,
        )
        self.assertIn("Items fetched : 3", result.output)

    def test_fetch_rejects_bad_header_pair(self) -> None:
        result = self.invoke([
            "fetch",
            "https://api.example.com/products",
            "--header",
            "Authorization",
        ])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Expected KEY:VALUE", result.output)

    def test_chunk_command_writes_json_for_local_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "chunks"
            input_dir.mkdir()
            markdown = input_dir / "guide.md"
            markdown.write_text(
                "\n".join([
                    "---",
                    "title: CLI Test Guide",
                    "path: https://example.com/cli-test",
                    "---",
                    "",
                    "# CLI Test Guide",
                    "",
                    "This file verifies that the CLI chunk command can read markdown",
                    "from disk and write chunk JSON output through the public command.",
                    "",
                    "## Details",
                    "",
                    "The content is deterministic and local.",
                ]),
                encoding="utf-8",
            )

            result = self.invoke([
                "chunk",
                "--input-dir",
                str(input_dir),
                "--output-dir",
                str(output_dir),
                "--chunk-size",
                "400",
                "--chunk-overlap",
                "40",
                "--min-chunk-length",
                "20",
            ])

            self.assertEqual(result.exit_code, 0, result.output)
            chunk_file = output_dir / "guide.json"
            self.assertTrue(chunk_file.exists(), result.output)
            chunks = json.loads(chunk_file.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(chunks), 1)
            self.assertEqual(chunks[0]["metadata"]["title"], "CLI Test Guide")

    def test_chunk_file_rejects_non_markdown_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "guide.txt"
            path.write_text("not markdown", encoding="utf-8")

            result = self.invoke(["chunk-file", str(path)])

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("Chunk input file must be markdown", result.output)

    def test_embed_passes_storage_options_to_sdk(self) -> None:
        expected = EmbedResult(
            files=1,
            chunks=2,
            input_dir="chunks",
            provider="qdrant",
            collection="rag_chunks",
            errors=[],
        )

        with patch.object(RagRails, "embed", return_value=expected) as embed:
            result = self.invoke([
                "embed",
                "--input-dir",
                "chunks",
                "--vector-db",
                "qdrant",
                "--collection",
                "rag_chunks",
                "--url",
                "http://localhost:6333",
                "--files",
                "guide.json",
                "--batch-size",
                "16",
                "--embedder",
                "voyage",
                "--model",
                "voyage-3",
            ])

        self.assertEqual(result.exit_code, 0, result.output)
        embed.assert_called_once_with(
            input_dir="chunks",
            vector_db="qdrant",
            collection="rag_chunks",
            url="http://localhost:6333",
            files=["guide.json"],
            batch_size=16,
            embedder="voyage",
            model="voyage-3",
        )
        self.assertIn("Chunks embedded: 2", result.output)

    def test_store_passes_storage_options_to_sdk(self) -> None:
        expected = StoreResult(
            files=1,
            chunks=2,
            input_dir="chunks",
            provider="qdrant",
            collection="rag_chunks",
            errors=[],
        )

        with patch.object(RagRails, "store", return_value=expected) as store:
            result = self.invoke([
                "store",
                "--input-dir",
                "chunks",
                "--vector-db",
                "qdrant",
                "--collection",
                "rag_chunks",
                "--url",
                "http://localhost:6333",
                "--files",
                "guide.json",
                "--batch-size",
                "16",
                "--embedder",
                "voyage",
                "--model",
                "voyage-3",
            ])

        self.assertEqual(result.exit_code, 0, result.output)
        store.assert_called_once_with(
            input_dir="chunks",
            vector_db="qdrant",
            collection="rag_chunks",
            url="http://localhost:6333",
            files=["guide.json"],
            batch_size=16,
            embedder="voyage",
            model="voyage-3",
        )
        self.assertIn("Chunks stored: 2", result.output)

    def test_retrieve_passes_query_and_rerank_options_to_sdk(self) -> None:
        expected = RetrieveResult(
            query="How do payouts work?",
            results=[
                RetrievedChunk(
                    id="chunk-1",
                    score=0.91,
                    text="Payouts are processed daily.",
                    metadata={"title": "Payments", "path": "/payments"},
                    rerank_score=0.97,
                )
            ],
        )

        with patch.object(RagRails, "retrieve", return_value=expected) as retrieve:
            result = self.invoke([
                "retrieve",
                "How do payouts work?",
                "--vector-db",
                "qdrant",
                "--collection",
                "rag_chunks",
                "--url",
                "http://localhost:6333",
                "--top-k",
                "20",
                "--embedder",
                "voyage",
                "--model",
                "voyage-3",
                "--rerank",
                "--reranker",
                "voyage",
                "--reranker-model",
                "rerank-2-lite",
                "--rerank-top-k",
                "5",
            ])

        self.assertEqual(result.exit_code, 0, result.output)
        retrieve.assert_called_once_with(
            "How do payouts work?",
            vector_db="qdrant",
            collection="rag_chunks",
            url="http://localhost:6333",
            top_k=20,
            embedder="voyage",
            model="voyage-3",
            rerank=True,
            reranker="voyage",
            reranker_model="rerank-2-lite",
            rerank_top_k=5,
        )
        self.assertIn("Results: 1", result.output)
        self.assertIn("rerank=0.9700", result.output)


if __name__ == "__main__":
    unittest.main()
