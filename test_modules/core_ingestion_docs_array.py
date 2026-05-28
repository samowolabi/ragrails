from __future__ import annotations

import json

from ragrails.core.stg_01_ingestors.docs.ingestor import ingest_docs


def main() -> None:
    result = ingest_docs(
        files=[
            {
                "path": "README.md",
                "title": "Repository README",
                "description": "Manual multi-document ingestion test",
            },
            "CHANGELOG.md",
        ]
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
