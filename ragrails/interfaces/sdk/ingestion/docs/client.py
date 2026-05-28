"""SDK methods for document ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from ragrails.types import ParseResult
from ragrails.interfaces.sdk.ingestion.utils.shared import save_outputs_to_dir
from ragrails.interfaces.sdk.ingestion.utils.frontmatter import with_frontmatter


SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".csv",
    ".docx",
    ".epub",
    ".html",
    ".htm",
    ".ipynb",
    ".json",
    ".md",
    ".msg",
    ".pdf",
    ".pptx",
    ".rss",
    ".tsv",
    ".txt",
    ".xls",
    ".xlsx",
    ".xml",
    ".zip",
}


class DocsMixin:
    def parse(
        self,
        files: str | list[str | dict] | None = None,
        *,
        folder: str | None = None,
        frontmatter: bool = False,
        output_format: Literal["markdown", "json"] = "markdown",
        output_dest: Literal["response", "file"] = "response",
        output_dir: str | None = None,
    ) -> ParseResult:
        """Convert local documents, file URLs, or raw bytes into markdown or JSON.

        Each item in ``files`` can be:

        - A local path string: ``"docs/report.pdf"``
        - A direct file URL string: ``"https://example.com/report.pdf"``
        - A path dict: ``{"path": "report.pdf", "title": "Report"}``
        - A bytes dict: ``{"content": b"...", "filename": "report.pdf", "title": "Report"}``

        The default behavior is response-only: outputs are returned in memory
        and no markdown/JSON files are written. Use ``output_dest="file"``
        with ``output_dir`` only when you explicitly want SDK convenience file
        output. ``frontmatter=True`` is also an SDK convenience and only
        modifies markdown text returned or saved by this method.

        ``output_format``: ``"markdown"`` (default) or ``"json"``.
        ``output_dest``: ``"response"`` (default) or ``"file"``.

        Example::

            result = rag.parse(files="report.pdf")
            result.outputs[0]["text"]

            result = rag.parse(files="report.pdf", output_format="json")
            result.outputs[0]

            rag.parse(files="report.pdf", output_dest="file", output_dir="files/output/docs")
            rag.parse(files="report.pdf", output_format="json", output_dest="file", output_dir="files/output/docs")
        """
        self._validate_parse_args(
            files=files,
            folder=folder,
            output_format=output_format,
            output_dest=output_dest,
            output_dir=output_dir,
        )

        try:
            from ragrails.core.stg_01_ingestors.docs import ingest_docs as _ingest_docs
        except ImportError as exc:
            raise RuntimeError("Document ingestion dependencies are missing. Reinstall with: pip install -U ragrails") from exc

        docs_input = self._discover_docs(folder) if folder else files
        docs = self._normalize_docs(docs_input)
        stats = _ingest_docs(docs)

        outputs = stats.get("outputs", [])
        if frontmatter and output_format == "markdown":
            outputs = with_frontmatter(outputs)
        if output_dest == "file":
            outputs = save_outputs_to_dir(outputs, output_dir, output_format)

        return ParseResult(
            documents=stats["documents"],
            failed=stats["failed"],
            outputs=outputs,
            errors=stats.get("errors", []),
        )

    @staticmethod
    def _validate_parse_args(
        *,
        files: str | list[str | dict] | None,
        folder: str | None,
        output_format: str,
        output_dest: str,
        output_dir: str | None,
    ) -> None:
        if files is None and folder is None:
            raise ValueError("Provide either 'files' or 'folder'")
        if files is not None and folder is not None:
            raise ValueError("Provide either 'files' or 'folder', not both")
        if output_format not in {"markdown", "json"}:
            raise ValueError(f"Invalid output_format '{output_format}' — use 'markdown' or 'json'")
        if output_dest not in {"response", "file"}:
            raise ValueError(f"Invalid output_dest '{output_dest}' — use 'response' or 'file'")
        if output_dest == "file" and not output_dir:
            raise ValueError("output_dir is required when output_dest is 'file'")

    @staticmethod
    def _discover_docs(folder: str) -> list[str]:
        base = Path(folder)
        if not folder:
            raise ValueError("folder is required")
        if not base.exists():
            raise FileNotFoundError(f"Document folder not found: {folder}")
        if not base.is_dir():
            raise NotADirectoryError(f"Document folder is not a directory: {folder}")

        files = [
            str(path)
            for path in sorted(base.iterdir())
            if path.is_file() and path.suffix.lower() in SUPPORTED_DOCUMENT_EXTENSIONS
        ]
        if not files:
            raise ValueError(f"No supported document files found in folder: {folder}")
        return files

    @staticmethod
    def _normalize_docs(files: str | list[str | dict]) -> list[dict]:
        file_list = [files] if isinstance(files, str) else list(files)
        if not file_list:
            raise ValueError("files must include at least one document")

        docs = []
        for item in file_list:
            if isinstance(item, str):
                if not item.strip():
                    raise ValueError("file names must be non-empty strings")
                if item.startswith(("http://", "https://")):
                    docs.append(DocsMixin._download_file(item))
                else:
                    DocsMixin._validate_document_extension(item)
                    stem = item.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                    docs.append({"path": item, "title": stem, "description": ""})
            elif isinstance(item, dict):
                if item.get("content") is not None:
                    filename = item.get("filename")
                    if not filename:
                        raise ValueError("Byte document entries must include 'filename'")
                    docs.append(item)
                else:
                    filename = item.get("path")
                    if not filename:
                        raise ValueError("Document dicts must include 'path'")
                    if not isinstance(filename, str) or not filename.strip():
                        raise ValueError("Document filename values must be non-empty strings")
                    if filename.startswith(("http://", "https://")):
                        downloaded = DocsMixin._download_file(filename)
                        downloaded["title"] = item.get("title") or downloaded["title"]
                        downloaded["description"] = item.get("description", "")
                        docs.append(downloaded)
                    else:
                        DocsMixin._validate_document_extension(filename)
                        stem = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                        docs.append({
                            "path": filename,
                            "title": item.get("title") or stem,
                            "description": item.get("description", ""),
                        })
            else:
                raise ValueError("files items must be strings or dicts")
        return docs

    @staticmethod
    def _validate_document_extension(filename: str) -> None:
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
            allowed = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
            raise ValueError(f"Unsupported document type '{suffix}' for '{filename}'. Supported extensions: {allowed}")

    @staticmethod
    def _download_file(url: str) -> dict:
        import urllib.request
        url_path = urlparse(url).path
        filename = url_path.rsplit("/", 1)[-1] or ""
        if not Path(filename).suffix:
            raise ValueError(f"Cannot determine file type from URL '{url}' — ensure the path ends with a file extension")
        DocsMixin._validate_document_extension(filename)
        try:
            with urllib.request.urlopen(url) as response:  # noqa: S310
                content = response.read()
        except Exception as exc:
            raise RuntimeError(f"Failed to download '{url}': {exc}") from exc
        return {
            "content": content,
            "filename": filename,
            "title": Path(filename).stem,
            "description": "",
            "source": url,
        }
