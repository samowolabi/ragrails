"""SDK methods for chunking."""

from __future__ import annotations

from pathlib import Path

from ragrails.types import ChunkResult
from ragrails.usage.sdk.shared import missing_extra


class ChunkingMixin:
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
            raise missing_extra("Chunking", "chunk", exc)

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
            raise missing_extra("Chunking", "chunk", exc)

        return _chunk_file(
            path,
            ChunkerConfig(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                min_chunk_length=min_chunk_length,
            ),
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
        ChunkingMixin._validate_chunk_numbers(
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
        ChunkingMixin._validate_chunk_numbers(
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
