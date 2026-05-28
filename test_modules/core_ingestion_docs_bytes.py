from __future__ import annotations

import json
from pathlib import Path

from ragrails.core.stg_01_ingestors.docs.ingestor import ingest_docs


def main() -> None:
    content = Path("README.md").read_bytes()
    result = ingest_docs(
        files=[
            {
                "filename": "README.md",
                "content": content,
                "content_type": "text/markdown",
                "source": "upload://README.md",
                "title": "Uploaded README",
                "description": "Manual byte document ingestion test",
            }
        ]
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
