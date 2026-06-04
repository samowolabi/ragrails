from __future__ import annotations

from pathlib import Path
import unittest

from click.testing import CliRunner

from ragrails.interfaces.cli.main import cli


class CliMainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_root_help_lists_stage_commands(self) -> None:
        result = self.runner.invoke(cli, ["--help"])

        self.assertEqual(result.exit_code, 0, result.output)
        for command in [
            "setup-url",
            "scrape",
            "parse",
            "fetch",
            "chunk",
            "embed",
            "store",
            "edit",
            "delete",
            "retrieve",
            "ingest",
            "query",
            "chat",
        ]:
            self.assertIn(command, result.output)

    def test_cli_modules_have_local_readmes(self) -> None:
        base = Path("ragrails/interfaces/cli")
        expected = {
            "README.md": ["setup-url", "scrape", "parse", "fetch", "chunk", "embed", "store", "edit", "delete", "retrieve", "ingest", "query", "chat"],
            "ingestion/README.md": ["setup-url", "scrape", "parse", "fetch"],
            "chunking/README.md": ["chunk"],
            "embedding/README.md": ["embed"],
            "storing/README.md": ["store", "edit", "delete"],
            "retrieval/README.md": ["retrieve"],
            "pipeline/README.md": ["ingest", "query"],
            "chat/README.md": ["chat"],
        }

        for relative_path, commands in expected.items():
            readme = base / relative_path
            self.assertTrue(readme.exists(), f"Missing CLI README: {readme}")
            content = readme.read_text(encoding="utf-8")
            for command in commands:
                self.assertIn(command, content, f"{readme} does not document {command}")

    def test_documented_cli_commands_are_registered(self) -> None:
        documented_commands = {
            "setup-url",
            "scrape",
            "parse",
            "fetch",
            "chunk",
            "embed",
            "store",
            "edit",
            "delete",
            "retrieve",
            "ingest",
            "query",
            "chat",
        }

        self.assertLessEqual(documented_commands, set(cli.commands))


if __name__ == "__main__":
    unittest.main()
