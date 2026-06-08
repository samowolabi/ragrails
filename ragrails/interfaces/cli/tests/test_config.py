from __future__ import annotations

from pathlib import Path
import unittest

from click.testing import CliRunner

from ragrails.interfaces.cli.config import load_config, save_config
from ragrails.interfaces.cli.main import cli


class CliConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_missing_config_returns_empty_defaults(self) -> None:
        with self.runner.isolated_filesystem():
            self.assertEqual(load_config(), {})

    def test_config_round_trips_expected_shape(self) -> None:
        config = {
            "vector_store": {"provider": "qdrant", "collection": "docs", "url": "http://localhost:6333"},
            "embedding": {"provider": "voyage", "model": "voyage-3"},
            "llm": {"provider": "openai", "model": "gpt-5.5", "max_tokens": 1024},
            "reranker": {"enabled": True, "provider": "voyage", "model": "rerank-2-lite"},
        }

        with self.runner.isolated_filesystem():
            path = save_config(config)

            self.assertEqual(Path(path).name, ".ragrails.toml")
            self.assertEqual(load_config(), config)

    def test_bare_ragrails_writes_project_config(self) -> None:
        user_input = "\n".join([
            "qdrant",
            "docs",
            "http://localhost:6333",
            "voyage",
            "voyage-3",
            "openai",
            "gpt-5.5",
            "1024",
            "n",
            "n",
            "",
        ])

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, [], input=user_input)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue(Path(".ragrails.toml").exists())
            self.assertEqual(load_config()["vector_store"]["collection"], "docs")
            self.assertIn("Saved config", result.output)
            self.assertIn("OPENAI_API_KEY", result.output)
            self.assertIn("VOYAGE_API_KEY", result.output)

    def test_bare_ragrails_qdrant_cloud_prints_api_key_hint(self) -> None:
        user_input = "\n".join([
            "qdrant_cloud",
            "docs",
            "https://cluster.example.qdrant.io",
            "voyage",
            "voyage-3",
            "openai",
            "gpt-5.5",
            "1024",
            "n",
            "n",
            "",
        ])

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, [], input=user_input)

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(load_config()["vector_store"]["provider"], "qdrant_cloud")
            self.assertIn("QDRANT_API_KEY", result.output)

    def test_bare_ragrails_writes_advanced_project_config(self) -> None:
        user_input = "\n".join([
            "qdrant",
            "docs",
            "",
            "voyage",
            "voyage-3",
            "openai",
            "gpt-5.5",
            "1024",
            "y",
            "voyage",
            "rerank-2-lite",
            "y",
            "1200",
            "150",
            "80",
            "32",
            "48",
            "7",
            "4",
            "y",
            "n",
            "y",
            "",
        ])

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, [], input=user_input)

            self.assertEqual(result.exit_code, 0, result.output)
            config = load_config()
            self.assertEqual(config["chunking"]["chunk_size"], 1200)
            self.assertEqual(config["embedding"]["batch_size"], 32)
            self.assertEqual(config["storage"]["batch_size"], 48)
            self.assertEqual(config["retrieval"]["top_k"], 7)
            self.assertEqual(config["retrieval"]["rerank_top_k"], 4)
            self.assertTrue(config["chat"]["query_rewrite"])
            self.assertFalse(config["chat"]["intent_routing"])
            self.assertTrue(config["chat"]["history_compaction"])

    def test_bare_ragrails_can_exit_when_config_exists(self) -> None:
        with self.runner.isolated_filesystem():
            save_config({"vector_store": {"provider": "qdrant", "collection": "docs"}})
            result = self.runner.invoke(cli, [], input="exit\n")

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn("Config unchanged.", result.output)

    def test_subcommand_does_not_trigger_setup(self) -> None:
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["retrieve", "--help"])

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertFalse(Path(".ragrails.toml").exists())
            self.assertNotIn("Saved config", result.output)


if __name__ == "__main__":
    unittest.main()
