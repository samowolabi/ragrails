from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ragrails.interfaces.sdk.ingestion.api import client as api_client
from ragrails.interfaces.sdk.ingestion.api.client import ApiMixin


def _make_output(name: str = "posts", page: int = 1) -> dict:
    return {
        "id": f"api_{name}_{page}",
        "display_id": f"00{page}_{name}",
        "title": f"{name.capitalize()} — page {page}",
        "text": f"# {name.capitalize()} — page {page}\n\nContent.",
        "source": f"https://api.example.com/{name}",
        "metadata": {"source_kind": "api", "file_type": "api", "page": page},
    }


def _make_stats(outputs: list[dict] | None = None, failed: int = 0) -> dict:
    outputs = outputs or [_make_output()]
    return {
        "documents": len(outputs),
        "failed": failed,
        "outputs": outputs,
        "errors": [],
    }


class _Rag(ApiMixin):
    pass


class ApiSDKTests(unittest.TestCase):

    # --- validation ---

    def test_raises_if_neither_url_nor_apis(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().fetch()

    def test_raises_if_both_url_and_apis(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().fetch("https://api.example.com/posts", apis=["https://api.example.com/users"])

    def test_raises_on_invalid_url_scheme(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().fetch("ftp://api.example.com/posts")

    def test_raises_on_invalid_method(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().fetch("https://api.example.com/posts", method="HEAD")

    def test_raises_if_max_pages_less_than_one(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().fetch("https://api.example.com/posts", max_pages=0)

    def test_raises_if_headers_not_dict(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().fetch("https://api.example.com/posts", headers="auth")

    def test_raises_on_invalid_output_format(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().fetch("https://api.example.com/posts", output_format="xml")

    def test_raises_on_invalid_output_dest(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().fetch("https://api.example.com/posts", output_dest="print")

    def test_raises_if_output_dest_file_without_output_dir(self) -> None:
        with self.assertRaises(ValueError):
            _Rag().fetch("https://api.example.com/posts", output_dest="file")

    # --- fetch response ---

    def test_fetch_single_url_returns_api_ingest_result(self) -> None:
        stats = _make_stats()
        with patch("ragrails.core.stg_01_ingestors.api.ingest_api", return_value=stats):
            result = _Rag().fetch("https://api.example.com/posts")

        self.assertEqual(result.documents, 1)
        self.assertEqual(result.failed, 0)
        self.assertEqual(len(result.outputs), 1)
        self.assertNotIn("output_path", result.outputs[0])
        self.assertEqual(result.errors, [])

    def test_fetch_batch_apis_passes_apis_to_core(self) -> None:
        stats = _make_stats(outputs=[_make_output("posts"), _make_output("users")])
        with patch("ragrails.core.stg_01_ingestors.api.ingest_api", return_value=stats) as mock_core:
            result = _Rag().fetch(apis=[
                "https://api.example.com/posts",
                {"url": "https://api.example.com/users", "title": "Users"},
            ])

        call_kwargs = mock_core.call_args[1] if mock_core.call_args[1] else {}
        self.assertEqual(result.documents, 2)

    def test_fetch_passes_timeout_to_core(self) -> None:
        stats = _make_stats()
        with patch("ragrails.core.stg_01_ingestors.api.ingest_api", return_value=stats) as mock_core:
            _Rag().fetch("https://api.example.com/posts", timeout=30.0)

        _, kwargs = mock_core.call_args
        self.assertEqual(kwargs.get("timeout"), 30.0)

    def test_fetch_markdown_format_includes_text_in_output(self) -> None:
        stats = _make_stats()
        with patch("ragrails.core.stg_01_ingestors.api.ingest_api", return_value=stats):
            result = _Rag().fetch("https://api.example.com/posts", output_format="markdown")

        self.assertIn("text", result.outputs[0])

    def test_fetch_json_format_includes_full_output_dict(self) -> None:
        stats = _make_stats(outputs=[_make_output()])
        with patch("ragrails.core.stg_01_ingestors.api.ingest_api", return_value=stats):
            result = _Rag().fetch("https://api.example.com/posts", output_format="json")

        self.assertIn("metadata", result.outputs[0])
        self.assertIn("source", result.outputs[0])

    # --- file output ---

    def test_fetch_saves_markdown_file_to_output_dir(self) -> None:
        output = _make_output()
        stats = _make_stats(outputs=[output])
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("ragrails.core.stg_01_ingestors.api.ingest_api", return_value=stats):
                result = _Rag().fetch(
                    "https://api.example.com/posts",
                    output_format="markdown",
                    output_dest="file",
                    output_dir=tmpdir,
                )

            saved_path = Path(result.outputs[0]["output_path"])
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.suffix, ".md")
            self.assertEqual(saved_path.read_text(encoding="utf-8"), output["text"])

    def test_fetch_saves_json_file_to_output_dir(self) -> None:
        output = _make_output()
        stats = _make_stats(outputs=[output])
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("ragrails.core.stg_01_ingestors.api.ingest_api", return_value=stats):
                result = _Rag().fetch(
                    "https://api.example.com/posts",
                    output_format="json",
                    output_dest="file",
                    output_dir=tmpdir,
                )

            saved_path = Path(result.outputs[0]["output_path"])
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.suffix, ".json")
            saved = json.loads(saved_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["id"], output["id"])

    def test_fetch_adds_output_path_to_every_output(self) -> None:
        stats = _make_stats(outputs=[_make_output("posts", 1), _make_output("posts", 2)])
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("ragrails.core.stg_01_ingestors.api.ingest_api", return_value=stats):
                result = _Rag().fetch(
                    "https://api.example.com/posts",
                    output_dest="file",
                    output_dir=tmpdir,
                )

        for item in result.outputs:
            self.assertIn("output_path", item)


if __name__ == "__main__":
    unittest.main()
