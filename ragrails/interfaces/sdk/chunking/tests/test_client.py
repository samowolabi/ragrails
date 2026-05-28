from __future__ import annotations

import unittest
from unittest.mock import patch

from ragrails.interfaces.sdk.chunking.client import ChunkingMixin


class _Rag(ChunkingMixin):
    pass


def _make_chunk(text: str = "Chunk text") -> dict:
    return {
        "id": "chunk-1",
        "source": "guide.md",
        "text": text,
        "embed_text": text,
        "metadata": {
            "source": "guide.md",
            "title": "Guide",
            "chunk_id": "chk_123",
        },
    }


class ChunkingSDKTests(unittest.TestCase):
    def test_chunk_string_returns_in_memory_result(self) -> None:
        stats = {"chunks": 1, "failed": 0, "outputs": [_make_chunk()], "errors": []}

        with patch("ragrails.core.stg_02_chunker.chunker.chunk_markdown_items", return_value=stats) as core:
            result = _Rag().chunk(
                markdown="# Guide\n\nUse Ragrails.",
                title="Guide",
                source="guide.md",
            )

        _, kwargs = core.call_args
        items = core.call_args[0][0]
        self.assertEqual(items[0]["text"], "# Guide\n\nUse Ragrails.")
        self.assertEqual(items[0]["source"], "guide.md")
        self.assertEqual(items[0]["metadata"]["title"], "Guide")
        self.assertEqual(kwargs["config"].chunk_size, 2000)
        self.assertEqual(result.inputs, 1)
        self.assertEqual(result.chunks, 1)
        self.assertEqual(result.items, stats["outputs"])
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.errors, [])

    def test_chunk_dict_array_normalizes_text_and_metadata(self) -> None:
        stats = {"chunks": 0, "failed": 0, "outputs": [], "errors": []}
        markdown = [
            {
                "text": "# Auth\n\nUse bearer tokens.",
                "source": "auth.md",
                "title": "Auth",
                "metadata": {"source_kind": "docs"},
            },
            {
                "text": "# Billing\n\nInvoices.",
                "source": "billing.md",
                "metadata": {"title": "Billing"},
            },
        ]

        with patch("ragrails.core.stg_02_chunker.chunker.chunk_markdown_items", return_value=stats) as core:
            result = _Rag().chunk(markdown=markdown, title="Fallback", source="fallback.md")

        items = core.call_args[0][0]
        self.assertEqual(result.inputs, 2)
        self.assertEqual(items[0]["text"], "# Auth\n\nUse bearer tokens.")
        self.assertEqual(items[0]["source"], "auth.md")
        self.assertEqual(items[0]["metadata"]["title"], "Auth")
        self.assertEqual(items[0]["metadata"]["source_kind"], "docs")
        self.assertEqual(items[1]["text"], "# Billing\n\nInvoices.")
        self.assertEqual(items[1]["source"], "billing.md")
        self.assertEqual(items[1]["metadata"]["title"], "Billing")

    def test_chunk_accepts_ingestion_outputs(self) -> None:
        stats = {"chunks": 1, "failed": 0, "outputs": [_make_chunk()], "errors": []}
        parsed_outputs = [
            {
                "id": "doc_123",
                "display_id": "report",
                "title": "Report",
                "text": "# Report\n\nParsed content.",
                "source": "/docs/report.pdf",
                "metadata": {
                    "source_kind": "docs",
                    "file_type": "pdf",
                    "description": "Annual report",
                },
            }
        ]

        with patch("ragrails.core.stg_02_chunker.chunker.chunk_markdown_items", return_value=stats) as core:
            result = _Rag().chunk(markdown=parsed_outputs)

        items = core.call_args[0][0]
        self.assertEqual(result.inputs, 1)
        self.assertEqual(items[0]["text"], "# Report\n\nParsed content.")
        self.assertEqual(items[0]["source"], "/docs/report.pdf")
        self.assertEqual(items[0]["metadata"]["title"], "Report")
        self.assertEqual(items[0]["metadata"]["source_kind"], "docs")
        self.assertEqual(items[0]["metadata"]["file_type"], "pdf")
        self.assertEqual(items[0]["metadata"]["description"], "Annual report")

    def test_chunk_forwards_config(self) -> None:
        stats = {"chunks": 0, "failed": 0, "outputs": [], "errors": []}

        with patch("ragrails.core.stg_02_chunker.chunker.chunk_markdown_items", return_value=stats) as core:
            _Rag().chunk(
                markdown="# Guide\n\nContent",
                chunk_size=500,
                chunk_overlap=50,
                min_chunk_length=20,
            )

        config = core.call_args.kwargs["config"]
        self.assertEqual(config.chunk_size, 500)
        self.assertEqual(config.chunk_overlap, 50)
        self.assertEqual(config.min_chunk_length, 20)

    def test_chunk_returns_structured_partial_failures_from_core(self) -> None:
        error = {
            "source": "bad.md",
            "source_kind": "markdown",
            "stage": "validate",
            "error": "chunk item text must be a non-empty string",
            "isRetryable": False,
            "attempts": 1,
        }
        stats = {"chunks": 1, "failed": 1, "outputs": [_make_chunk()], "errors": [error]}

        with patch("ragrails.core.stg_02_chunker.chunker.chunk_markdown_items", return_value=stats):
            result = _Rag().chunk(markdown=["# Good\n\nContent"])

        self.assertEqual(result.chunks, 1)
        self.assertEqual(result.failed, 1)
        self.assertEqual(result.errors, [error])

    def test_chunk_rejects_empty_markdown_string(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().chunk(markdown=" ")

    def test_chunk_rejects_empty_markdown_list(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().chunk(markdown=[])

    def test_chunk_rejects_invalid_document_item(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().chunk(markdown=[object()])

    def test_chunk_rejects_missing_text_in_document_dict(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().chunk(markdown=[{"source": "missing.md"}])

    def test_chunk_rejects_text_aliases(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-empty 'text'"):
            _Rag().chunk(markdown=[{"markdown": "# Old alias"}])
        with self.assertRaisesRegex(ValueError, "non-empty 'text'"):
            _Rag().chunk(markdown=[{"content": "# Old alias"}])

    def test_chunk_rejects_invalid_numbers(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().chunk(markdown="# Guide", chunk_size=0)
        with self.assertRaises(ValueError):
            _Rag().chunk(markdown="# Guide", chunk_overlap=-1)
        with self.assertRaises(ValueError):
            _Rag().chunk(markdown="# Guide", chunk_size=10, chunk_overlap=10)
        with self.assertRaises(ValueError):
            _Rag().chunk(markdown="# Guide", min_chunk_length=0)


if __name__ == "__main__":
    unittest.main()
