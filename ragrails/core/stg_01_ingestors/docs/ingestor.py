"""Document ingestor.

PDF: tries pymupdf4llm first (better layout), falls back to markitdown.
All other formats: markitdown.
Results are returned in memory.
"""

import os
import hashlib
import tempfile
import time
import uuid
from pathlib import Path

import pymupdf4llm
from markitdown import MarkItDown


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

_EXT_TYPE = {
    ".pdf": "pdf",
    ".csv": "csv",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".pptx": "pptx",
    ".txt": "txt",
    ".html": "html",
    ".htm": "html",
    ".md": "md",
}


def _type_from_ext(ext: str) -> str:
    return _EXT_TYPE.get(ext.lower(), "doc")


def _use_pymupdf4llm(input_file: str) -> tuple[str, str] | None:
    try:
        return pymupdf4llm.to_markdown(input_file), "pymupdf4llm"
    except Exception:
        return None


def _use_markitdown(input_file: str) -> tuple[str, str] | None:
    try:
        return MarkItDown().convert(input_file).text_content, "markitdown"
    except Exception:
        return None


def _convert(input_file: str) -> tuple[str, str]:
    ext = os.path.splitext(input_file)[1].lower()
    if ext == ".pdf":
        return _use_pymupdf4llm(input_file) or _use_markitdown(input_file) or ("", "")
    return _use_markitdown(input_file) or ("", "")


def _ingest_doc_path(
    path: str,
    title: str,
    description: str,
) -> dict:
    """Convert a single document to markdown and return it."""
    start = time.time()

    try:
        _validate_path_input(path)
        content, converter = _convert(path)
    except Exception as e:
        return _failure(source=path, source_kind="path", stage="validate", error=str(e))

    elapsed = time.time() - start

    if not content:
        return _failure(source=path, source_kind="path", stage="convert", error="no content extracted")

    ext = os.path.splitext(path)[1]
    source = os.path.abspath(path)

    basename = os.path.splitext(os.path.basename(path))[0]
    size_bytes = len(content.encode())
    return _success(
        source=source,
        title=title,
        text=content,
        description=description,
        extension=ext,
        size_bytes=size_bytes,
        converter=converter,
        elapsed_seconds=elapsed,
        output_id=_document_id(source, content),
        display_id=basename,
    )


def _ingest_doc_bytes(
    content: bytes,
    filename: str,
    title: str,
    description: str = "",
    content_type: str | None = None,
    source: str | None = None,
) -> dict:
    """Convert uploaded/in-memory document bytes to markdown and return it."""
    try:
        _validate_bytes_input(content, filename)
        original_name = Path(filename).name
        suffix = Path(original_name).suffix.lower()
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / f"ragrails_upload_{uuid.uuid4().hex}{suffix}"
            temp_path.write_bytes(bytes(content))
            converted = _ingest_doc_path(
                path=str(temp_path),
                title=title,
                description=description,
            )
    except Exception as e:
        return _failure(source=source or filename, source_kind="bytes", stage="validate", error=str(e))

    if converted["error"]:
        converted["error"]["source"] = source or filename
        converted["error"]["source_kind"] = "bytes"
        return converted

    output = converted["output"]
    resolved_source = source or filename
    converted_text = output["text"]
    output["source"] = resolved_source
    output["id"] = _document_id(resolved_source, converted_text)
    output["display_id"] = Path(filename).stem

    output["metadata"].update({
        "description": description,
        "file_type": _type_from_ext(suffix),
        "size_bytes": len(content),
        "source_kind": "bytes",
    })
    if content_type:
        output["metadata"]["content_type"] = content_type

    return {"output": output, "error": None}


def ingest_docs(
    files: list[str | dict],
) -> dict:
    """Convert document path/byte entries to markdown."""
    if not files:
        return {"documents": 0, "failed": 0, "outputs": [], "errors": []}

    results = []
    for item in files:
        try:
            doc = _normalize_doc_input(item)
        except Exception as e:
            results.append(_failure(
                source=_doc_error_source(item),
                source_kind=_doc_error_source_kind(item),
                stage="validate",
                error=str(e),
            ))
            continue

        if doc["kind"] == "bytes":
            result = _ingest_doc_bytes(
                content=doc["content"],
                filename=doc["filename"],
                title=doc["title"],
                description=doc["description"],
                content_type=doc["content_type"],
                source=doc["source"],
            )
        else:
            result = _ingest_doc_path(
                path=doc["path"],
                title=doc["title"],
                description=doc["description"],
            )
        results.append(result)

    outputs = [r["output"] for r in results if r.get("output")]
    errors = [r["error"] for r in results if r.get("error")]
    failed = len(errors)
    return {"documents": len(outputs), "failed": failed, "outputs": outputs, "errors": errors}


def _normalize_doc_input(item: str | dict) -> dict:
    if isinstance(item, str):
        path = item
        title = os.path.splitext(os.path.basename(path))[0]
        return {"kind": "path", "path": path, "title": title, "description": ""}

    content = item.get("content")
    if content is not None:
        filename = item.get("filename") or item.get("name") or item.get("path")
        if not filename:
            raise ValueError("Byte document entries must include 'filename', 'name', or 'path'")
        return {
            "kind": "bytes",
            "content": content,
            "filename": filename,
            "title": item.get("title") or os.path.splitext(os.path.basename(filename))[0],
            "description": item.get("description", ""),
            "content_type": item.get("content_type"),
            "source": item.get("source") or filename,
        }

    path = item.get("path") or item.get("file") or item.get("filename")
    if not path:
        raise ValueError("Document entries must include path/file/filename or byte content")

    return {
        "kind": "path",
        "path": path,
        "title": item.get("title") or os.path.splitext(os.path.basename(path))[0],
        "description": item.get("description", ""),
    }


def _validate_path_input(path: str) -> None:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("document path must be a non-empty string")

    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"document path not found: {path}")
    if not file_path.is_file():
        raise IsADirectoryError(f"document path is not a file: {path}")

    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        raise ValueError(f"unsupported document type '{suffix}' for '{path}'. Supported extensions: {allowed}")


def _validate_bytes_input(content: bytes, filename: str) -> None:
    if not isinstance(content, (bytes, bytearray)):
        raise TypeError("content must be bytes")
    if len(content) == 0:
        raise ValueError("content must not be empty")
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("filename is required for byte document input")

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
        raise ValueError(f"unsupported document type '{suffix}' for '{filename}'. Supported extensions: {allowed}")


def _doc_error_source(item: str | dict) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        value = (
            item.get("source")
            or item.get("path")
            or item.get("file")
            or item.get("filename")
            or item.get("name")
        )
        if value:
            return str(value)
    return str(item)


def _doc_error_source_kind(item: str | dict) -> str:
    if isinstance(item, dict) and item.get("content") is not None:
        return "bytes"
    return "path"


def _success(
    *,
    source: str,
    title: str,
    text: str,
    description: str,
    extension: str,
    size_bytes: int,
    converter: str,
    elapsed_seconds: float,
    output_id: str,
    display_id: str,
) -> dict:
    return {
        "output": {
            "id": output_id,
            "display_id": display_id,
            "source": source,
            "title": title,
            "text": text,
            "metadata": {
                "description": description,
                "file_type": _type_from_ext(extension),
                "size_bytes": size_bytes,
                "converter": converter,
                "elapsed_seconds": elapsed_seconds,
                "source_kind": "path",
            },
        },
        "error": None,
    }


def _failure(
    *,
    source: str,
    source_kind: str,
    stage: str,
    error: str,
    attempts: int = 1,
) -> dict:
    return {
        "output": None,
        "error": {
            "source": source,
            "source_kind": source_kind,
            "stage": stage,
            "error": error,
            "isRetryable": False,
            "attempts": attempts,
        },
    }


def _document_id(source: str, text: str) -> str:
    digest = hashlib.sha256(f"{source}\n{text}".encode("utf-8")).hexdigest()[:16]
    return f"doc_{digest}"
