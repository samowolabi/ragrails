from __future__ import annotations

import json
import os
import unittest
from unittest.mock import Mock, patch

from click.testing import CliRunner

from ragrails.interfaces.cli.config import save_config
from ragrails.interfaces.cli.main import cli


class CliDoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_doctor_fails_when_config_is_missing(self) -> None:
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["doctor"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("FAIL", result.output)
        self.assertIn(".ragrails.toml was not found", result.output)
        self.assertIn("Run ragrails", result.output)

    def test_doctor_passes_for_complete_local_config(self) -> None:
        env = {
            "OPENAI_API_KEY": "test-openai",
            "VOYAGE_API_KEY": "test-voyage",
        }
        with self.runner.isolated_filesystem():
            save_config(_config())
            with patch.dict(os.environ, env, clear=False):
                with patch("ragrails.interfaces.cli.doctor.commands._can_import", return_value=True):
                    result = self.runner.invoke(cli, ["doctor"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("OK", result.output)
        self.assertIn("connections: Skipped live service checks.", result.output)

    def test_doctor_json_reports_failures(self) -> None:
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["doctor", "--json"])

        self.assertEqual(result.exit_code, 1)
        payload = json.loads(result.output)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["checks"][0]["status"], "fail")

    def test_doctor_can_check_qdrant_connection(self) -> None:
        response = Mock(status_code=200)
        env = {
            "OPENAI_API_KEY": "test-openai",
            "VOYAGE_API_KEY": "test-voyage",
        }
        with self.runner.isolated_filesystem():
            save_config(_config())
            with patch.dict(os.environ, env, clear=False):
                with patch("ragrails.interfaces.cli.doctor.commands._can_import", return_value=True):
                    with patch("httpx.get", return_value=response) as get:
                        result = self.runner.invoke(cli, ["doctor", "--connections"])

        self.assertEqual(result.exit_code, 0, result.output)
        get.assert_called_once()
        self.assertIn("Qdrant responded", result.output)


def _config() -> dict:
    return {
        "vector_store": {
            "provider": "qdrant",
            "collection": "docs",
            "url": "http://localhost:6333",
        },
        "embedding": {
            "provider": "voyage",
            "model": "voyage-3",
        },
        "llm": {
            "provider": "openai",
            "model": "gpt-5.5",
            "max_tokens": 1024,
        },
        "reranker": {
            "enabled": False,
            "provider": "voyage",
            "model": "rerank-2-lite",
        },
    }


if __name__ == "__main__":
    unittest.main()
