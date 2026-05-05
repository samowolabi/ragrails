"""
Table utilities for the chunker.

Responsibilities:
  - Detect markdown table blocks within text
  - Segment text into (content, is_table) pairs
  - Parse table headers for metadata enrichment
"""

import re


def segment_tables(text: str) -> list[tuple[str, bool]]:
    """Split text into (content, is_table) segments.

    Contiguous runs of lines starting with '|' are marked as table blocks.
    Non-'|' lines between two '|' lines are kept inside the table block.

    Example:
        segment_tables("Intro text.\n| Col1 | Col2 |\n|------|------|\n| a | b |")
        # → [("Intro text.", False), ("| Col1 | Col2 |\n|------|------|\n| a | b |", True)]
    """
    segments: list[tuple[str, bool]] = []
    lines = text.split("\n")
    buf_lines: list[str] = []
    in_table = False

    for i, line in enumerate(lines):
        is_table_row = line.strip().startswith("|")

        if not in_table and is_table_row:
            if buf_lines:
                content = "\n".join(buf_lines)
                if segments and not content.startswith("\n"):
                    content = "\n" + content
                segments.append((content, False))
            buf_lines = []
            in_table = True

        elif in_table and not is_table_row:
            lookahead = lines[i + 1: i + 21]
            if not any(l.strip().startswith("|") for l in lookahead):
                if buf_lines:
                    content = "\n".join(buf_lines)
                    if segments and not content.startswith("\n"):
                        content = "\n" + content
                    segments.append((content, True))
                buf_lines = []
                in_table = False

        buf_lines.append(line)

    if buf_lines:
        content = "\n".join(buf_lines)
        if segments and not content.startswith("\n"):
            content = "\n" + content
        segments.append((content, in_table))

    return segments


def parse_headers(table: str) -> list[str]:
    """Extract column header names from a markdown table string.

    Example:
        parse_headers("| Bank Name | Code | Currency |\n|-----------|------|----------|\n| GTBank | 058 | NGN |")
        # → ["Bank Name", "Code", "Currency"]
    """
    for line in table.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and not re.match(r"^\|[-| :]+\|$", stripped):
            return [cell.strip() for cell in stripped.strip("|").split("|")]
    return []


def _parse_rows(table: str) -> tuple[str, str, list[str]]:
    """Return (header_line, separator_line, data_rows) from a markdown table."""
    lines = [l for l in table.splitlines() if l.strip()]
    if len(lines) < 2:
        return "", "", lines

    header = lines[0]
    separator = lines[1] if re.match(r"^\|[-| :]+\|$", lines[1].strip()) else ""
    data = lines[2:] if separator else lines[1:]
    return header, separator, data


def chunk_table(table: str, chunk_size: int, rows_per_chunk: int = 20) -> list[str]:
    """Split a large markdown table into size-aware chunks.

    Each chunk repeats the original header and separator so every chunk remains
    understandable after retrieval. `rows_per_chunk` is kept as a secondary cap
    so a table with many tiny rows does not produce overly dense chunks.

    Example:
        chunk_table("| Name | Code |\n|------|------|\n| GTBank | 058 |\n| Access | 044 |", chunk_size=80, rows_per_chunk=1)
        # → ["| Name | Code |\n|------|------|\n| GTBank | 058 |",
        #    "| Name | Code |\n|------|------|\n| Access | 044 |"]
    """
    header, separator, data = _parse_rows(table)
    if not data:
        return [table]

    prefix = f"{header}\n{separator}\n" if separator else f"{header}\n"
    chunks = []
    batch: list[str] = []

    def emit() -> None:
        if batch:
            chunks.append(prefix + "\n".join(batch))
            batch.clear()

    for row in data:
        candidate_rows = batch + [row]
        candidate = prefix + "\n".join(candidate_rows)
        if batch and (len(candidate) > chunk_size or len(candidate_rows) > rows_per_chunk):
            emit()
        batch.append(row)

    emit()

    return chunks
