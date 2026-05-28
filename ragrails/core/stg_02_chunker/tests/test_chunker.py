from __future__ import annotations

import unittest

from ragrails.core.stg_02_chunker.chunker import chunk_markdown, chunk_markdown_items
from ragrails.core.stg_02_chunker.config import ChunkerConfig


class ChunkerCoreTests(unittest.TestCase):
    def config(self) -> ChunkerConfig:
        return ChunkerConfig(chunk_size=400, chunk_overlap=40, min_chunk_length=20)

    def test_chunk_markdown_uses_explicit_metadata_without_frontmatter(self) -> None:
        chunks = chunk_markdown(
            "# Guide\n\nThis is useful documentation for a developer workflow.",
            source="manual://guide",
            metadata={
                "title": "Guide",
                "description": "Developer docs",
                "source_kind": "manual",
                "original_type": "manual",
            },
            config=self.config(),
        )

        self.assertEqual(len(chunks), 1)
        chunk = chunks[0]
        self.assertIn("id", chunk)
        self.assertEqual(chunk["source"], "manual://guide")
        self.assertIn("# Guide", chunk["text"])
        self.assertIn("This is useful documentation for a developer workflow.", chunk["text"])
        self.assertIn("embed_text", chunk)
        self.assertIn("Guide", chunk["embed_text"])
        self.assertEqual(chunk["metadata"]["source"], "manual://guide")
        self.assertEqual(chunk["metadata"]["source_kind"], "manual")
        self.assertEqual(chunk["metadata"]["title"], "Guide")
        self.assertEqual(chunk["metadata"]["description"], "Developer docs")
        self.assertEqual(chunk["metadata"]["original_type"], "manual")
        self.assertEqual(chunk["metadata"]["heading"], {"h1": "Guide"})
        self.assertTrue(chunk["metadata"]["chunk_id"].startswith("chk_"))

    def test_chunk_markdown_does_not_parse_frontmatter(self) -> None:
        chunks = chunk_markdown(
            "---\ntitle: Not Metadata\n---\n\n# Real Title\n\nEnough body content to survive minimum chunk length.",
            source="manual://frontmatter",
            metadata={"title": "Explicit Title"},
            config=self.config(),
        )

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["metadata"]["title"], "Explicit Title")

    def test_chunk_markdown_items_returns_structured_result(self) -> None:
        result = chunk_markdown_items(
            [
                {
                    "text": "# One\n\nEnough content for the first markdown item.",
                    "source": "manual://one",
                    "title": "One",
                },
                {
                    "markdown": "# Two\n\nEnough content for the second markdown item.",
                    "source": "manual://two",
                    "metadata": {"title": "Two"},
                },
            ],
            config=self.config(),
        )

        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["chunks"], 2)
        self.assertEqual(len(result["outputs"]), 2)
        self.assertEqual(result["outputs"][0]["source"], "manual://one")
        self.assertEqual(result["outputs"][1]["source"], "manual://two")

    def test_chunk_markdown_items_collects_standard_errors(self) -> None:
        result = chunk_markdown_items(
            [
                {"source": "manual://bad", "title": "Bad"},
                {
                    "text": "# Good\n\nEnough content for the good markdown item.",
                    "source": "manual://good",
                    "title": "Good",
                },
            ],
            config=self.config(),
        )

        self.assertEqual(result["chunks"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["errors"], [
            {
                "source": "manual://bad",
                "source_kind": "markdown",
                "stage": "validate",
                "error": "chunk item text must be a non-empty string",
                "isRetryable": False,
                "attempts": 1,
            }
        ])

    def test_chunk_markdown_items_rejects_non_list_input(self) -> None:
        result = chunk_markdown_items({"text": "# Bad"})

        self.assertEqual(result, {
            "chunks": 0,
            "failed": 1,
            "outputs": [],
            "errors": [
                {
                    "source": "",
                    "source_kind": "markdown",
                    "stage": "validate",
                    "error": "items must be a list",
                    "isRetryable": False,
                    "attempts": 1,
                }
            ],
        })

    def test_chunk_markdown_validates_config(self) -> None:
        with self.assertRaisesRegex(ValueError, "chunk_overlap must be smaller than chunk_size"):
            chunk_markdown(
                "# Bad\n\nEnough content for invalid config test.",
                config=ChunkerConfig(chunk_size=100, chunk_overlap=100, min_chunk_length=10),
            )

    def test_table_chunks_receive_table_metadata(self) -> None:
        result = chunk_markdown_items(
            [
                {
                    "text": "\n".join([
                        "# Pricing",
                        "",
                        "| Plan | Price |",
                        "| --- | --- |",
                        "| Basic | 10 |",
                        "| Pro | 20 |",
                    ]),
                    "source": "manual://pricing",
                    "title": "Pricing",
                }
            ],
            config=ChunkerConfig(chunk_size=80, chunk_overlap=0, min_chunk_length=10),
        )

        table_chunks = [chunk for chunk in result["outputs"] if "table_id" in chunk["metadata"]]
        self.assertTrue(table_chunks)
        table = table_chunks[0]
        self.assertEqual(table["metadata"]["columns"], ["Plan", "Price"])
        self.assertTrue(table["metadata"]["table_id"].startswith("tbl_"))
        self.assertEqual(table["metadata"]["row_start"], 1)
        self.assertGreaterEqual(table["metadata"]["row_end"], 1)

    def test_header_strategy_preserves_heading_context_per_chunk(self) -> None:
        chunks = chunk_markdown(
            "\n".join([
                "# Payments",
                "",
                "Payments let customers pay merchants with reliable checkout content.",
                "",
                "## Cards",
                "",
                "Card payments require authorization and settlement details.",
                "",
                "### Webhooks",
                "",
                "Webhook events notify merchants when payment status changes.",
            ]),
            source="manual://payments",
            metadata={"title": "Payments"},
            config=ChunkerConfig(chunk_size=140, chunk_overlap=0, min_chunk_length=20),
        )

        headings = [chunk["metadata"]["heading"] for chunk in chunks]
        self.assertIn({"h1": "Payments"}, headings)
        self.assertIn({"h1": "Payments", "h2": "Cards"}, headings)
        self.assertIn({"h1": "Payments", "h2": "Cards", "h3": "Webhooks"}, headings)

    def test_code_blocks_are_kept_atomic(self) -> None:
        chunks = chunk_markdown(
            "\n".join([
                "# SDK",
                "",
                "Use this example to initialize the SDK before making requests.",
                "",
                "```python",
                "from ragrails import RagRails",
                "rag = RagRails()",
                "result = rag.chunk(markdown='# Guide\\n\\nContent')",
                "print(result.chunks)",
                "```",
                "",
                "The example should remain readable after chunking.",
            ]),
            source="manual://sdk",
            metadata={"title": "SDK"},
            config=ChunkerConfig(chunk_size=120, chunk_overlap=0, min_chunk_length=20),
        )

        code_chunks = [chunk for chunk in chunks if "```python" in chunk["text"]]
        self.assertEqual(len(code_chunks), 1)
        self.assertIn("print(result.chunks)", code_chunks[0]["text"])
        self.assertIn("```", code_chunks[0]["text"])

    def test_large_tables_are_split_with_headers_repeated(self) -> None:
        rows = [f"| Plan {i} | {i * 10} |" for i in range(1, 6)]
        chunks = chunk_markdown(
            "\n".join([
                "# Pricing",
                "",
                "| Plan | Price |",
                "| --- | --- |",
                *rows,
            ]),
            source="manual://pricing-table",
            metadata={"title": "Pricing"},
            config=ChunkerConfig(chunk_size=80, chunk_overlap=0, min_chunk_length=10),
        )

        table_chunks = [chunk for chunk in chunks if "table_id" in chunk["metadata"]]
        self.assertGreater(len(table_chunks), 1)
        table_ids = {chunk["metadata"]["table_id"] for chunk in table_chunks}
        self.assertEqual(len(table_ids), 1)
        for chunk in table_chunks:
            self.assertIn("| Plan | Price |", chunk["text"])
            self.assertEqual(chunk["metadata"]["columns"], ["Plan", "Price"])

    def test_split_markdown_links_are_repaired(self) -> None:
        chunks = chunk_markdown(
            (
                "# Links\n\n"
                "Read the complete integration guide at [Ragrails Integration Guide]"
                "(https://example.com/docs/integration-guide) before deploying. "
                "This paragraph has enough extra content to force splitting."
            ),
            source="manual://links",
            metadata={"title": "Links"},
            config=ChunkerConfig(chunk_size=90, chunk_overlap=0, min_chunk_length=20),
        )

        combined = "\n".join(chunk["text"] for chunk in chunks)
        self.assertIn("](https://example.com/docs/integration-guide)", combined)
        self.assertNotIn("[Ragrails Integration Guide]\n", combined)
        self.assertNotIn("\n](https://example.com/docs/integration-guide)", combined)

    def test_navigation_only_chunks_are_dropped_and_trailing_nav_is_stripped(self) -> None:
        chunks = chunk_markdown(
            "\n".join([
                "# Guide",
                "",
                "[Skip to main content](#main)",
                "",
                "Use Ragrails to prepare documents for retrieval workflows. "
                "This section has enough substantive explanatory content to avoid "
                "being treated as navigation.",
                "",
                "[Home](/)",
                "[Next](/next)",
            ]),
            source="manual://nav",
            metadata={"title": "Guide"},
            config=ChunkerConfig(chunk_size=120, chunk_overlap=0, min_chunk_length=20),
        )

        all_text = "\n".join(chunk["text"] for chunk in chunks)
        self.assertNotIn("Skip to main content", all_text)
        self.assertNotIn("[Home](/)", chunks[-1]["text"])
        self.assertNotIn("[Next](/next)", chunks[-1]["text"])

    def test_tracking_pixels_and_trailing_horizontal_rules_are_removed(self) -> None:
        chunks = chunk_markdown(
            "\n".join([
                "# Cleanup",
                "",
                "This chunk has meaningful content for retrieval workflows.",
                "",
                "![](https://example.com/tracker.gif)",
                "",
                "---",
            ]),
            source="manual://cleanup",
            metadata={"title": "Cleanup"},
            config=self.config(),
        )

        self.assertEqual(len(chunks), 1)
        self.assertNotIn("tracker.gif", chunks[0]["text"])
        self.assertFalse(chunks[0]["text"].rstrip().endswith("---"))

    def test_content_hash_and_ids_are_stable_for_same_source_and_content(self) -> None:
        markdown = "# Stable\n\nStable chunk identity helps avoid duplicate embeddings."
        first = chunk_markdown(markdown, source="manual://stable", config=self.config())
        second = chunk_markdown(markdown, source="manual://stable", config=self.config())

        self.assertEqual(first[0]["id"], second[0]["id"])
        self.assertEqual(first[0]["metadata"]["id"], second[0]["metadata"]["id"])
        self.assertEqual(first[0]["metadata"]["chunk_id"], second[0]["metadata"]["chunk_id"])
        self.assertEqual(first[0]["metadata"]["content_hash"], second[0]["metadata"]["content_hash"])

    def test_embed_text_combines_title_heading_description_and_text(self) -> None:
        chunks = chunk_markdown(
            "# Auth\n\nUse bearer tokens for authenticated requests.",
            source="manual://auth",
            metadata={"title": "API Guide", "description": "Authentication docs"},
            config=self.config(),
        )

        embed_text = chunks[0]["embed_text"]
        self.assertTrue(embed_text.startswith("API Guide\nAuth\nAuthentication docs\n\n"))
        self.assertIn("Use bearer tokens for authenticated requests.", embed_text)


if __name__ == "__main__":
    unittest.main()
