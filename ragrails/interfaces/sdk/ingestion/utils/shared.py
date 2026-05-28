"""Optional file-output utilities for SDK ingestion methods.

SDK ingestion returns data in memory by default. These helpers are only used
when a caller explicitly passes output_dest="file".
"""

from __future__ import annotations

import json
from pathlib import Path


def save_outputs_to_dir(outputs: list[dict], output_dir: str, output_format: str) -> list[dict]:
    """Write each output to a file and return outputs with output_path added."""
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)
    ext = ".md" if output_format == "markdown" else ".json"
    saved = []
    for output in outputs:
        name = output.get("display_id") or output.get("title") or output.get("id") or "output"
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(name))
        path = base / f"{safe_name}{ext}"
        if output_format == "markdown":
            path.write_text(output.get("text", ""), encoding="utf-8")
        else:
            path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
        saved.append({**output, "output_path": str(path)})
    return saved
