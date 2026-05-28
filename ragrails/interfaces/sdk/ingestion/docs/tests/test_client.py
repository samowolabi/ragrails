from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from ragrails.interfaces.sdk.ingestion.docs import client as docs_client
from ragrails.interfaces.sdk.ingestion.docs.client import DocsMixin


def _make_output(name: str = "report") -> dict:
    return {
        "id": f"doc_{name}",
        "display_id": name,
        "title": name.capitalize(),
        "text": f"# {name.capitalize()}\n\nContent.",
        "source": f"/tmp/{name}.pdf",
        "metadata": {"file_type": "pdf"},
    }


def _make_stats(outputs: list[dict] | None = None, failed: int = 0) -> dict:
    outputs = outputs or [_make_output()]
    return {
        "documents": len(outputs),
        "failed": failed,
        "outputs": outputs,
        "errors": [],
    }


class _Rag(DocsMixin):
    pass


class DocsSDKTests(unittest.TestCase):

    # --- validation ---

    def test_raises_if_neither_files_nor_folder(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().parse()

    def test_raises_if_both_files_and_folder(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().parse(files="report.pdf", folder="docs/")

    def test_raises_on_invalid_output_format(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().parse(files="report.pdf", output_format="xml")

    def test_raises_on_invalid_output_dest(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().parse(files="report.pdf", output_dest="print")

    def test_raises_if_output_dest_file_without_output_dir(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().parse(files="report.pdf", output_dest="file")

    # --- parse response ---

    def test_parse_returns_documents_count_and_outputs(self) -> None:
        stats = _make_stats()
        with patch.object(docs_client.DocsMixin, "_normalize_docs", return_value=[{}]):
            with patch("ragrails.core.stg_01_ingestors.docs.ingest_docs", return_value=stats):
                result = _Rag().parse(files="report.pdf")

        self.assertEqual(result.documents, 1)
        self.assertEqual(result.failed, 0)
        self.assertEqual(len(result.outputs), 1)
        self.assertNotIn("output_path", result.outputs[0])
        self.assertEqual(result.errors, [])

    def test_parse_markdown_format_includes_text_in_output(self) -> None:
        stats = _make_stats()
        with patch.object(docs_client.DocsMixin, "_normalize_docs", return_value=[{}]):
            with patch("ragrails.core.stg_01_ingestors.docs.ingest_docs", return_value=stats):
                result = _Rag().parse(files="report.pdf", output_format="markdown")

        self.assertIn("text", result.outputs[0])

    def test_parse_json_format_includes_full_output_dict(self) -> None:
        stats = _make_stats(outputs=[_make_output()])
        with patch.object(docs_client.DocsMixin, "_normalize_docs", return_value=[{}]):
            with patch("ragrails.core.stg_01_ingestors.docs.ingest_docs", return_value=stats):
                result = _Rag().parse(files="report.pdf", output_format="json")

        self.assertIn("metadata", result.outputs[0])
        self.assertIn("source", result.outputs[0])

    # --- parse file output ---

    def test_parse_saves_markdown_file_to_output_dir(self) -> None:
        output = _make_output()
        stats = _make_stats(outputs=[output])
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(docs_client.DocsMixin, "_normalize_docs", return_value=[{}]):
                with patch("ragrails.core.stg_01_ingestors.docs.ingest_docs", return_value=stats):
                    result = _Rag().parse(
                        files="report.pdf",
                        output_format="markdown",
                        output_dest="file",
                        output_dir=tmpdir,
                    )

            saved_path = Path(result.outputs[0]["output_path"])
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.suffix, ".md")
            self.assertEqual(saved_path.read_text(encoding="utf-8"), output["text"])

    def test_parse_saves_json_file_to_output_dir(self) -> None:
        output = _make_output()
        stats = _make_stats(outputs=[output])
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(docs_client.DocsMixin, "_normalize_docs", return_value=[{}]):
                with patch("ragrails.core.stg_01_ingestors.docs.ingest_docs", return_value=stats):
                    result = _Rag().parse(
                        files="report.pdf",
                        output_format="json",
                        output_dest="file",
                        output_dir=tmpdir,
                    )

            saved_path = Path(result.outputs[0]["output_path"])
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.suffix, ".json")
            saved = json.loads(saved_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["id"], output["id"])

    def test_parse_adds_output_path_to_every_output(self) -> None:
        stats = _make_stats(outputs=[_make_output("a"), _make_output("b")])
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(docs_client.DocsMixin, "_normalize_docs", return_value=[{}, {}]):
                with patch("ragrails.core.stg_01_ingestors.docs.ingest_docs", return_value=stats):
                    result = _Rag().parse(
                        files=["a.pdf", "b.pdf"],
                        output_dest="file",
                        output_dir=tmpdir,
                    )

        for item in result.outputs:
            self.assertIn("output_path", item)

    # --- normalize docs ---

    def test_normalize_string_path_becomes_dict(self) -> None:
        docs = DocsMixin._normalize_docs("docs/report.pdf")
        self.assertEqual(docs[0]["path"], "docs/report.pdf")
        self.assertEqual(docs[0]["title"], "report")

    def test_normalize_bytes_dict_passes_through_unchanged(self) -> None:
        item = {"content": b"abc", "filename": "report.pdf", "title": "Report"}
        docs = DocsMixin._normalize_docs([item])
        self.assertEqual(docs[0], item)

    def test_normalize_bytes_dict_missing_filename_raises(self) -> None:
        with self.assertRaises(ValueError):
            DocsMixin._normalize_docs([{"content": b"abc"}])

    def test_normalize_dict_without_path_or_filename_raises(self) -> None:
        with self.assertRaises(ValueError):
            DocsMixin._normalize_docs([{"title": "Report"}])

    def test_normalize_path_dict(self) -> None:
        docs = DocsMixin._normalize_docs([{"path": "docs/report.pdf", "title": "Report"}])
        self.assertEqual(docs[0]["path"], "docs/report.pdf")
        self.assertEqual(docs[0]["title"], "Report")

    def test_normalize_rejects_legacy_path_aliases(self) -> None:
        with self.assertRaisesRegex(ValueError, "include 'path'"):
            DocsMixin._normalize_docs([{"filename": "docs/report.pdf"}])
        with self.assertRaisesRegex(ValueError, "include 'path'"):
            DocsMixin._normalize_docs([{"file": "docs/report.pdf"}])

    def test_normalize_rejects_legacy_byte_filename_aliases(self) -> None:
        with self.assertRaisesRegex(ValueError, "include 'filename'"):
            DocsMixin._normalize_docs([{"content": b"abc", "name": "report.pdf"}])
        with self.assertRaisesRegex(ValueError, "include 'filename'"):
            DocsMixin._normalize_docs([{"content": b"abc", "path": "report.pdf"}])

    def test_normalize_unsupported_extension_raises(self) -> None:
        with self.assertRaises(ValueError):
            DocsMixin._normalize_docs("report.exe")

    def test_normalize_empty_string_raises(self) -> None:
        with self.assertRaises(ValueError):
            DocsMixin._normalize_docs("   ")

    def test_normalize_empty_list_raises(self) -> None:
        with self.assertRaises(ValueError):
            DocsMixin._normalize_docs([])

    def test_normalize_url_string_calls_download_file(self) -> None:
        fake = {"content": b"pdf", "filename": "report.pdf", "title": "report", "description": "", "source": "https://example.com/report.pdf"}
        with patch.object(DocsMixin, "_download_file", return_value=fake) as mock_dl:
            docs = DocsMixin._normalize_docs("https://example.com/report.pdf")
        mock_dl.assert_called_once_with("https://example.com/report.pdf")
        self.assertEqual(docs[0], fake)

    def test_normalize_url_in_dict_preserves_title_and_description(self) -> None:
        fake = {"content": b"pdf", "filename": "report.pdf", "title": "report", "description": "", "source": "https://example.com/report.pdf"}
        with patch.object(DocsMixin, "_download_file", return_value=dict(fake)):
            docs = DocsMixin._normalize_docs([{
                "path": "https://example.com/report.pdf",
                "title": "My Report",
                "description": "Annual report",
            }])
        self.assertEqual(docs[0]["title"], "My Report")
        self.assertEqual(docs[0]["description"], "Annual report")

    # --- discover docs ---

    def test_discover_docs_returns_only_supported_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.pdf").write_bytes(b"")
            (Path(tmpdir) / "b.md").write_text("", encoding="utf-8")
            (Path(tmpdir) / "c.exe").write_bytes(b"")
            files = DocsMixin._discover_docs(tmpdir)
        self.assertEqual(len(files), 2)
        self.assertTrue(all(f.endswith(".pdf") or f.endswith(".md") for f in files))

    def test_discover_docs_raises_if_folder_not_found(self) -> None:
        with self.assertRaises(FileNotFoundError):
            DocsMixin._discover_docs("/nonexistent/path")

    def test_discover_docs_raises_if_no_supported_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "file.exe").write_bytes(b"")
            with self.assertRaises(ValueError):
                DocsMixin._discover_docs(tmpdir)

    # --- download file ---

    def test_download_file_raises_if_url_has_no_extension(self) -> None:
        with self.assertRaises(ValueError):
            DocsMixin._download_file("https://example.com/report")

    def test_download_file_raises_on_unsupported_extension(self) -> None:
        with self.assertRaises(ValueError):
            DocsMixin._download_file("https://example.com/file.exe")

    def test_download_file_raises_on_network_failure(self) -> None:
        with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
            with self.assertRaises(RuntimeError):
                DocsMixin._download_file("https://example.com/report.pdf")

    def test_download_file_returns_bytes_dict_on_success(self) -> None:
        mock_response = MagicMock()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.read.return_value = b"%PDF"

        with patch("urllib.request.urlopen", return_value=mock_response):
            result = DocsMixin._download_file("https://example.com/report.pdf")

        self.assertEqual(result["content"], b"%PDF")
        self.assertEqual(result["filename"], "report.pdf")
        self.assertEqual(result["title"], "report")
        self.assertEqual(result["source"], "https://example.com/report.pdf")


if __name__ == "__main__":
    unittest.main()
