from __future__ import annotations

from pathlib import Path
import unittest

from ragrails.interfaces.server.app import create_app


class ServerAppTests(unittest.TestCase):
    def test_app_registers_sdk_backed_routes(self) -> None:
        app = create_app()
        paths = {getattr(route, "path", "") for route in app.routes}

        expected = {
            "/v1/health",
            "/v1/ingest/api",
            "/v1/ingest/url",
            "/v1/ingest/url/stream",
            "/v1/ingest/docs",
            "/v1/ingest/docs/upload",
            "/v1/chunk",
            "/v1/embed",
            "/v1/store",
            "/v1/edit",
            "/v1/delete",
            "/v1/retrieve",
            "/v1/pipelines/ingest",
            "/v1/pipelines/query",
            "/v1/chat",
            "/v1/chat/stream",
        }

        self.assertLessEqual(expected, paths)

    def test_server_modules_have_local_readmes(self) -> None:
        base = Path("ragrails/interfaces/server")
        expected = {
            "README.md": ["/v1/health", "/v1/chat", "/v1/pipelines/ingest"],
            "ingestion/README.md": ["/v1/ingest/api", "/v1/ingest/url", "/v1/ingest/url/stream", "/v1/ingest/docs", "/v1/ingest/docs/upload"],
            "chunking/README.md": ["/v1/chunk"],
            "embedding/README.md": ["/v1/embed"],
            "storing/README.md": ["/v1/store", "/v1/edit", "/v1/delete"],
            "retrieval/README.md": ["/v1/retrieve"],
            "pipeline/README.md": ["/v1/pipelines/ingest", "/v1/pipelines/query"],
            "chat/README.md": ["/v1/chat", "/v1/chat/stream"],
        }

        for relative_path, markers in expected.items():
            readme = base / relative_path
            self.assertTrue(readme.exists(), f"Missing REST README: {readme}")
            content = readme.read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, content, f"{readme} does not document {marker}")


if __name__ == "__main__":
    unittest.main()
