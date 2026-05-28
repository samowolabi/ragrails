from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ragrails.core.stg_01_ingestors.docs import ingestor


class DocsIngestorTests(unittest.TestCase):
    def test_ingest_path_success_returns_clean_in_memory_document(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "guide.md"
            path.write_text("# ignored by patched converter", encoding="utf-8")

            with patch.object(ingestor, "_convert", return_value=("# Guide\n\nContent.", "markitdown")):
                result = ingestor.ingest_docs(files=[{
                    "path": str(path),
                    "title": "Guide",
                    "description": "Developer guide",
                }])

        self.assertEqual(result["documents"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["errors"], [])

        output = result["outputs"][0]
        self.assertTrue(output["id"].startswith("doc_"))
        self.assertEqual(output["display_id"], "guide")
        self.assertEqual(output["title"], "Guide")
        self.assertEqual(output["text"], "# Guide\n\nContent.")
        self.assertFalse(output["text"].startswith("---"))
        self.assertEqual(output["metadata"]["description"], "Developer guide")
        self.assertEqual(output["metadata"]["file_type"], "md")
        self.assertEqual(output["metadata"]["converter"], "markitdown")
        self.assertEqual(output["metadata"]["source_kind"], "path")
        self.assertEqual(output["metadata"]["size_bytes"], len("# Guide\n\nContent.".encode()))
        self.assertGreaterEqual(output["metadata"]["elapsed_seconds"], 0)

    def test_ingest_bytes_success_uses_upload_source_and_metadata(self) -> None:
        seen_paths = []

        def fake_convert(path: str):
            seen_paths.append(Path(path))
            return "# Upload\n\nContent.", "markitdown"

        with patch.object(ingestor, "_convert", side_effect=fake_convert):
            result = ingestor.ingest_docs(files=[{
                "filename": "../unsafe name.md",
                "content": b"# raw upload",
                "content_type": "text/markdown",
                "source": "upload://unsafe-name.md",
                "title": "Uploaded Guide",
                "description": "Uploaded document",
            }])

        self.assertEqual(result["documents"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["errors"], [])
        self.assertEqual(len(seen_paths), 1)
        self.assertTrue(seen_paths[0].name.startswith("ragrails_upload_"))
        self.assertEqual(seen_paths[0].suffix, ".md")

        output = result["outputs"][0]
        self.assertTrue(output["id"].startswith("doc_"))
        self.assertEqual(output["display_id"], "unsafe name")
        self.assertEqual(output["source"], "upload://unsafe-name.md")
        self.assertEqual(output["title"], "Uploaded Guide")
        self.assertEqual(output["text"], "# Upload\n\nContent.")
        self.assertEqual(output["metadata"]["source_kind"], "bytes")
        self.assertEqual(output["metadata"]["file_type"], "md")
        self.assertEqual(output["metadata"]["size_bytes"], len(b"# raw upload"))
        self.assertEqual(output["metadata"]["content_type"], "text/markdown")

    def test_invalid_path_returns_standard_error(self) -> None:
        result = ingestor.ingest_docs(files=["missing.pdf"])

        self.assertEqual(result["documents"], 0)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["outputs"], [])
        self.assertEqual(result["errors"], [
            {
                "source": "missing.pdf",
                "source_kind": "path",
                "stage": "validate",
                "error": "document path not found: missing.pdf",
                "isRetryable": False,
                "attempts": 1,
            }
        ])

    def test_invalid_bytes_returns_standard_error(self) -> None:
        result = ingestor.ingest_docs(files=[{
            "filename": "bad.exe",
            "content": b"abc",
        }])

        self.assertEqual(result["documents"], 0)
        self.assertEqual(result["failed"], 1)
        error = result["errors"][0]
        self.assertEqual(error["source"], "bad.exe")
        self.assertEqual(error["source_kind"], "bytes")
        self.assertEqual(error["stage"], "validate")
        self.assertIn("unsupported document type '.exe'", error["error"])
        self.assertFalse(error["isRetryable"])
        self.assertEqual(error["attempts"], 1)

    def test_malformed_entry_does_not_stop_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "guide.md"
            path.write_text("# ignored by patched converter", encoding="utf-8")

            with patch.object(ingestor, "_convert", return_value=("# Guide", "markitdown")):
                result = ingestor.ingest_docs(files=[
                    {"title": "bad"},
                    str(path),
                ])

        self.assertEqual(result["documents"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(len(result["outputs"]), 1)
        self.assertEqual(result["errors"], [
            {
                "source": "{'title': 'bad'}",
                "source_kind": "path",
                "stage": "validate",
                "error": "Document entries must include path/file/filename or byte content",
                "isRetryable": False,
                "attempts": 1,
            }
        ])

    def test_no_content_returns_convert_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "empty.md"
            path.write_text("# ignored by patched converter", encoding="utf-8")

            with patch.object(ingestor, "_convert", return_value=("", "")):
                result = ingestor.ingest_docs(files=[str(path)])

        self.assertEqual(result["documents"], 0)
        self.assertEqual(result["failed"], 1)
        error = result["errors"][0]
        self.assertEqual(error["source"], str(path))
        self.assertEqual(error["source_kind"], "path")
        self.assertEqual(error["stage"], "convert")
        self.assertEqual(error["error"], "no content extracted")
        self.assertFalse(error["isRetryable"])
        self.assertEqual(error["attempts"], 1)


if __name__ == "__main__":
    unittest.main()
