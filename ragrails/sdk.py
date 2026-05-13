"""Class-based SDK entrypoint for Ragrails."""

from __future__ import annotations

import asyncio
import concurrent.futures
import subprocess
import sys
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from .types import ApiIngestResult, ChunkResult, ParseResult, ScrapeResult, StoreResult


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


def _run_async(coro):
    """Run a coroutine, even when called from inside a running event loop (e.g. Jupyter)."""
    try:
        asyncio.get_running_loop()
        # Already inside a loop (Jupyter, IPython) — run in a fresh thread
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    except RuntimeError:
        return asyncio.run(coro)


def _missing_extra(feature: str, extra: str, error: ImportError) -> RuntimeError:
    wrapped = RuntimeError(
        f"{feature} requires optional dependencies. Install them with: "
        f'pip install "ragrails[{extra}]"'
    )
    wrapped.__cause__ = error
    return wrapped


class RagRails:
    """Main public SDK client.

    Example:
        from ragrails import RagRails

        result = RagRails().scrape(
            url=["https://example.com"],
            mode="full",
            output_dir="files/output/web_crawled",
        )
    """

    def setup_url(self, *, browser: str = "chromium") -> dict:
        """Install the Playwright browser binary needed by URL ingestion.

        Example:
            from ragrails import RagRails

            RagRails().setup_url()

        In Jupyter, this runs against the same Python executable as the active
        kernel, avoiding the common "browser executable does not exist" error.
        """
        if not browser or not browser.strip():
            raise ValueError("browser is required")

        try:
            import playwright  # noqa: F401
        except ImportError as exc:
            raise _missing_extra("URL setup", "url", exc)

        command = [sys.executable, "-m", "playwright", "install", browser]
        completed = subprocess.run(command, check=False)
        if completed.returncode != 0:
            raise RuntimeError(
                "Failed to install Playwright browser binary. "
                f"Run manually: {' '.join(command)}"
            )

        return {
            "browser": browser,
            "command": command,
            "returncode": completed.returncode,
        }

    def scrape(
        self,
        url: str | list[str],
        *,
        mode: Literal["each", "full"] = "each",
        output_dir: str = "files/output/web_crawled",
        frontmatter: bool = True,
        dlq_path: str | None = None,
        max_depth: int = 3,
        max_pages: int = 200,
    ) -> ScrapeResult:
        """Scrape exact URLs or crawl a full site into markdown files."""
        resolved_dlq_path = dlq_path or str(Path(output_dir) / "dlq.json")
        self._validate_scrape_args(
            url=url,
            mode=mode,
            output_dir=output_dir,
            dlq_path=resolved_dlq_path,
            max_depth=max_depth,
            max_pages=max_pages,
        )

        try:
            from ragrails.pipeline.stg_01_ingestors.config import UrlIngestorConfig
            from ragrails.pipeline.stg_01_ingestors.url import scrape_url
        except ImportError as exc:
            raise _missing_extra("URL ingestion", "url", exc)

        config = UrlIngestorConfig(
            output_dir=output_dir,
            dlq_path=resolved_dlq_path,
            max_depth=max_depth,
            max_pages=max_pages,
        )
        stats = _run_async(
            scrape_url(
                urls=url,
                mode=mode,
                config=config,
                frontmatter=frontmatter,
            )
        )
        return ScrapeResult(
            pages=stats["pages"],
            failed=stats["failed"],
            output_dir=output_dir,
            files=stats.get("files", []),
            dlq_path=resolved_dlq_path,
            errors=stats.get("errors", []),
        )

    def retry_scrape(
        self,
        dlq_path: str,
        *,
        mode: Literal["each", "full"] = "each",
        max_depth: int = 3,
        max_pages: int = 200,
        max_attempts: int = 3,
    ) -> ScrapeResult:
        """Retry failed URLs recorded in the scrape dead-letter queue."""
        output_dir = str(Path(dlq_path).parent)
        self._validate_retry_scrape_args(
            mode=mode,
            output_dir=output_dir,
            dlq_path=dlq_path,
            max_depth=max_depth,
            max_pages=max_pages,
            max_attempts=max_attempts,
        )

        try:
            from ragrails.pipeline.stg_01_ingestors.config import UrlIngestorConfig
            from ragrails.pipeline.stg_01_ingestors.url import retry_dlq
        except ImportError as exc:
            raise _missing_extra("URL ingestion", "url", exc)

        config = UrlIngestorConfig(
            output_dir=output_dir,
            dlq_path=dlq_path,
            max_depth=max_depth,
            max_pages=max_pages,
        )
        stats = _run_async(
            retry_dlq(
                mode=mode,
                config=config,
                max_attempts=max_attempts,
            )
        )
        return ScrapeResult(
            pages=stats["pages"],
            failed=stats["failed"],
            output_dir=output_dir,
            files=stats.get("files", []),
            dlq_path=dlq_path,
            errors=stats.get("errors", []),
        )

    @staticmethod
    def _validate_scrape_args(
        *,
        url: str | list[str],
        mode: str,
        output_dir: str,
        dlq_path: str,
        max_depth: int,
        max_pages: int,
    ) -> None:
        if mode not in {"each", "full"}:
            raise ValueError(f"Invalid mode '{mode}' — use 'each' or 'full'")
        if not output_dir:
            raise ValueError("output_dir is required")
        if not dlq_path:
            raise ValueError("dlq_path is required")
        if max_depth < 0:
            raise ValueError("max_depth must be greater than or equal to 0")
        if max_pages < 1:
            raise ValueError("max_pages must be greater than 0")

        urls = [url] if isinstance(url, str) else list(url)
        if not urls:
            raise ValueError("url must include at least one URL")

        for item in urls:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("url values must be non-empty strings")
            parsed = urlparse(item)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Invalid URL '{item}' — use an absolute http(s) URL")

    @staticmethod
    def _validate_retry_scrape_args(
        *,
        mode: str,
        output_dir: str,
        dlq_path: str,
        max_depth: int,
        max_pages: int,
        max_attempts: int,
    ) -> None:
        if mode not in {"each", "full"}:
            raise ValueError(f"Invalid mode '{mode}' — use 'each' or 'full'")
        if not output_dir:
            raise ValueError("output_dir is required")
        if not dlq_path:
            raise ValueError("dlq_path is required")
        if max_depth < 0:
            raise ValueError("max_depth must be greater than or equal to 0")
        if max_pages < 1:
            raise ValueError("max_pages must be greater than 0")
        if max_attempts < 1:
            raise ValueError("max_attempts must be greater than 0")

    def parse(
        self,
        files: str | list[str | dict] | None = None,
        *,
        folder: str | None = None,
        input_dir: str = "files/input",
        output_dir: str = "files/output/docs",
        frontmatter: bool = True,
    ) -> ParseResult:
        """Convert local documents into markdown files.

        `files` can be a single filename, a list of filenames, or dicts with
        `filename`, `title`, and `description` for custom metadata.
        `folder` converts all supported files in that folder.
        """
        self._validate_parse_args(
            files=files,
            folder=folder,
            input_dir=input_dir,
            output_dir=output_dir,
        )

        try:
            from ragrails.pipeline.stg_01_ingestors.config import DocsIngestorConfig
            from ragrails.pipeline.stg_01_ingestors.docs import ingest_docs as _ingest_docs
        except ImportError as exc:
            raise RuntimeError("Document ingestion dependencies are missing. Reinstall with: pip install -U ragrails") from exc

        docs_input = self._discover_docs(folder) if folder else files
        docs = self._normalize_docs(docs_input)
        config = DocsIngestorConfig(
            input_dir=folder or input_dir,
            output_dir=output_dir,
        )
        stats = _ingest_docs(docs=docs, config=config, frontmatter=frontmatter)
        return ParseResult(
            documents=stats["documents"],
            failed=stats["failed"],
            output_dir=output_dir,
            files=stats["files"],
            errors=stats.get("errors", []),
        )

    @staticmethod
    def _validate_parse_args(
        *,
        files: str | list[str | dict] | None,
        folder: str | None,
        input_dir: str,
        output_dir: str,
    ) -> None:
        if files is None and folder is None:
            raise ValueError("Provide either 'files' or 'folder'")
        if files is not None and folder is not None:
            raise ValueError("Provide either 'files' or 'folder', not both")
        if not output_dir:
            raise ValueError("output_dir is required")
        if folder is None and not input_dir:
            raise ValueError("input_dir is required when using files")

    def fetch(
        self,
        url: str,
        *,
        title: str = "API Response",
        description: str = "",
        method: str = "GET",
        headers: dict | None = None,
        params: dict | None = None,
        body: dict | None = None,
        pagination: dict | None = None,
        max_pages: int = 100,
        output_dir: str = "files/output/api",
        frontmatter: bool = True,
    ) -> ApiIngestResult:
        """Fetch a REST API endpoint and save response pages as markdown."""
        self._validate_fetch_args(
            url=url,
            method=method,
            headers=headers,
            params=params,
            body=body,
            pagination=pagination,
            max_pages=max_pages,
            output_dir=output_dir,
        )

        try:
            from ragrails.pipeline.stg_01_ingestors.api import ingest_api as _ingest_api
            from ragrails.pipeline.stg_01_ingestors.config import ApiIngestorConfig
        except ImportError as exc:
            raise RuntimeError("API ingestion dependencies are missing. Reinstall with: pip install -U ragrails") from exc

        config = ApiIngestorConfig(output_dir=output_dir, max_pages=max_pages)
        stats = _run_async(
            _ingest_api(
                url=url,
                title=title,
                description=description,
                method=method,
                headers=headers,
                params=params,
                body=body,
                pagination=pagination,
                max_pages=max_pages,
                config=config,
                frontmatter=frontmatter,
            )
        )
        return ApiIngestResult(
            pages=stats["pages"],
            items=stats["items"],
            failed=stats["failed"],
            output_dir=output_dir,
            files=stats["files"],
            errors=stats.get("errors", []),
        )

    def chunk(
        self,
        *,
        input_dir: str = "files/output/web_crawled",
        output_dir: str = "files/output/chunks",
        chunk_size: int = 2000,
        chunk_overlap: int = 200,
        min_chunk_length: int = 100,
    ) -> ChunkResult:
        """Split markdown files in a directory into RAG chunk JSON files."""
        self._validate_chunk_args(
            input_dir=input_dir,
            output_dir=output_dir,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )
        try:
            from ragrails.pipeline.stg_02_chunker.chunker import chunk_dir as _chunk_dir
            from ragrails.pipeline.stg_02_chunker.config import ChunkerConfig
        except ImportError as exc:
            raise _missing_extra("Chunking", "chunk", exc)

        stats = _chunk_dir(ChunkerConfig(
            input_dir=input_dir,
            output_dir=output_dir,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        ))
        return ChunkResult(
            files=stats["files"],
            chunks=stats["chunks"],
            output_dir=output_dir,
            output_files=stats["output_files"],
            failed=stats["failed"],
            errors=stats["errors"],
        )

    def chunk_file(
        self,
        path: str,
        *,
        chunk_size: int = 2000,
        chunk_overlap: int = 200,
        min_chunk_length: int = 100,
    ) -> list[dict]:
        """Split one markdown file and return chunks in memory."""
        self._validate_chunk_file_args(
            path=path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )
        try:
            from ragrails.pipeline.stg_02_chunker.chunker import chunk_file as _chunk_file
            from ragrails.pipeline.stg_02_chunker.config import ChunkerConfig
        except ImportError as exc:
            raise _missing_extra("Chunking", "chunk", exc)

        return _chunk_file(
            path,
            ChunkerConfig(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                min_chunk_length=min_chunk_length,
            ),
        )

    def store(
        self,
        *,
        input_dir: str = "files/output/chunks",
        vector_db: Literal["qdrant", "pinecone", "weaviate"] = "qdrant",
        collection: str | None = None,
        url: str | None = None,
        files: str | list[str] | None = None,
        batch_size: int = 64,
        embedder: str = "voyage",
        model: str = "voyage-3",
    ) -> StoreResult:
        """Embed chunk JSON files and store them in the configured vector DB."""
        normalized_files = self._normalize_store_files(files)
        self._validate_store_args(
            input_dir=input_dir,
            vector_db=vector_db,
            collection=collection,
            files=normalized_files,
            batch_size=batch_size,
            embedder=embedder,
            model=model,
        )

        install_extra = f"store-{vector_db}" if embedder == "voyage" else f"{embedder},{vector_db}"
        try:
            from ragrails.models.embedder.config import EmbedderConfig as ModelEmbedderConfig
            from ragrails.models.embedder.config import create_embedder
            from ragrails.models.vector_db.registry import create_vector_store
            from ragrails.pipeline.stg_03_embedder.config import EmbedderConfig as StoreConfig
            from ragrails.pipeline.stg_03_embedder.embedder import embed_chunks

            embedding_model = create_embedder(
                ModelEmbedderConfig(provider=embedder, model=model),
                input_type="document",
            )
            vector_store = create_vector_store(
                provider=vector_db,
                url=url,
                collection=collection,
            )
            stats = embed_chunks(
                model=embedding_model,
                store=vector_store,
                config=StoreConfig(batch_size=batch_size, input_type="document", input_dir=input_dir),
                files=normalized_files,
            )
        except ImportError as exc:
            raise _missing_extra("Vector storage", install_extra, exc)
        return StoreResult(
            files=stats["files"],
            chunks=stats["chunks"],
            input_dir=stats["input_dir"],
            provider=stats["provider"],
            collection=stats["collection"],
            errors=stats["errors"],
        )

    @staticmethod
    def _validate_chunk_args(
        *,
        input_dir: str,
        output_dir: str,
        chunk_size: int,
        chunk_overlap: int,
        min_chunk_length: int,
    ) -> None:
        if not input_dir:
            raise ValueError("input_dir is required")
        if not output_dir:
            raise ValueError("output_dir is required")
        base = Path(input_dir)
        if not base.exists():
            raise FileNotFoundError(f"Chunk input directory not found: {input_dir}")
        if not base.is_dir():
            raise NotADirectoryError(f"Chunk input path is not a directory: {input_dir}")
        if not any(path.is_file() and path.suffix.lower() == ".md" for path in base.iterdir()):
            raise ValueError(f"No markdown files found in input_dir: {input_dir}")
        RagRails._validate_chunk_numbers(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )

    @staticmethod
    def _validate_chunk_file_args(
        *,
        path: str,
        chunk_size: int,
        chunk_overlap: int,
        min_chunk_length: int,
    ) -> None:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("path must be a non-empty string")
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Chunk input file not found: {path}")
        if not file_path.is_file():
            raise IsADirectoryError(f"Chunk input path is not a file: {path}")
        if file_path.suffix.lower() != ".md":
            raise ValueError(f"Chunk input file must be markdown: {path}")
        RagRails._validate_chunk_numbers(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_length=min_chunk_length,
        )

    @staticmethod
    def _validate_chunk_numbers(
        *,
        chunk_size: int,
        chunk_overlap: int,
        min_chunk_length: int,
    ) -> None:
        if chunk_size < 1:
            raise ValueError("chunk_size must be greater than 0")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be greater than or equal to 0")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if min_chunk_length < 1:
            raise ValueError("min_chunk_length must be greater than 0")

    @staticmethod
    def _normalize_store_files(files: str | list[str] | None) -> list[str] | None:
        if files is None:
            return None
        normalized = [files] if isinstance(files, str) else list(files)
        if not normalized:
            raise ValueError("files must include at least one chunk JSON filename")
        for filename in normalized:
            if not isinstance(filename, str) or not filename.strip():
                raise ValueError("files values must be non-empty strings")
        return normalized

    @staticmethod
    def _validate_store_args(
        *,
        input_dir: str,
        vector_db: str,
        collection: str | None,
        files: list[str] | None,
        batch_size: int,
        embedder: str,
        model: str,
    ) -> None:
        if vector_db not in {"qdrant", "pinecone", "weaviate"}:
            raise ValueError("vector_db must be one of: qdrant, pinecone, weaviate")
        if not input_dir:
            raise ValueError("input_dir is required")
        if batch_size < 1:
            raise ValueError("batch_size must be greater than 0")
        if not embedder:
            raise ValueError("embedder is required")
        if not model:
            raise ValueError("model is required")
        if vector_db == "pinecone" and collection and "_" in collection:
            raise ValueError("Pinecone collection/index names cannot contain underscores. Use hyphens, e.g. 'rag-chunks'.")
        if vector_db == "weaviate" and collection and not collection.isalnum():
            raise ValueError("Weaviate collection names must contain only letters and digits, e.g. 'RagChunks'.")
        if vector_db == "weaviate" and collection and not collection[:1].isupper():
            raise ValueError("Weaviate collection names must start with an uppercase letter, e.g. 'RagChunks'.")

        base = Path(input_dir)
        if not base.exists():
            raise FileNotFoundError(f"Store input directory not found: {input_dir}")
        if not base.is_dir():
            raise NotADirectoryError(f"Store input path is not a directory: {input_dir}")

        paths = [base / filename for filename in files] if files else sorted(base.glob("*.json"))
        if not paths:
            raise ValueError(f"No chunk JSON files found in input_dir: {input_dir}")
        for path in paths:
            if path.suffix.lower() != ".json":
                raise ValueError(f"Store input file must be JSON: {path.name}")
            if not path.exists():
                raise FileNotFoundError(f"Store input file not found: {path}")
            if not path.is_file():
                raise IsADirectoryError(f"Store input path is not a file: {path}")

    @staticmethod
    def _validate_fetch_args(
        *,
        url: str,
        method: str,
        headers: dict | None,
        params: dict | None,
        body: dict | None,
        pagination: dict | None,
        max_pages: int,
        output_dir: str,
    ) -> None:
        if not isinstance(url, str) or not url.strip():
            raise ValueError("url must be a non-empty string")
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Invalid URL '{url}' — use an absolute http(s) URL")

        allowed_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
        if method.upper() not in allowed_methods:
            allowed = ", ".join(sorted(allowed_methods))
            raise ValueError(f"Invalid method '{method}' — use one of: {allowed}")
        if not output_dir:
            raise ValueError("output_dir is required")
        if max_pages < 1:
            raise ValueError("max_pages must be greater than 0")

        for name, value in {
            "headers": headers,
            "params": params,
            "body": body,
            "pagination": pagination,
        }.items():
            if value is not None and not isinstance(value, dict):
                raise ValueError(f"{name} must be a dict when provided")

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
            path.name
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
                RagRails._validate_document_extension(item)
                stem = item.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                docs.append({"filename": item, "title": stem, "description": ""})
            else:
                filename = item.get("filename") or item.get("file")
                if not filename:
                    raise ValueError("Document dicts must include 'filename' or 'file'")
                if not isinstance(filename, str) or not filename.strip():
                    raise ValueError("Document filename values must be non-empty strings")
                RagRails._validate_document_extension(filename)
                stem = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                docs.append({
                    "filename": filename,
                    "title": item.get("title") or stem,
                    "description": item.get("description", ""),
                })
        return docs

    @staticmethod
    def _validate_document_extension(filename: str) -> None:
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_DOCUMENT_EXTENSIONS:
            allowed = ", ".join(sorted(SUPPORTED_DOCUMENT_EXTENSIONS))
            raise ValueError(f"Unsupported document type '{suffix}' for '{filename}'. Supported extensions: {allowed}")
