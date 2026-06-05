from __future__ import annotations

import unittest
from unittest.mock import patch

from ragrails.models.llm.config import LLMConfig, create_llm
from ragrails.models.llm.registry import get
from ragrails.models.llm.usage_logger import _cost


class FakeProviderModule:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, *, model: str, max_tokens: int):
        self.calls.append({"model": model, "max_tokens": max_tokens})
        return {"model": model, "max_tokens": max_tokens}


class LLMConfigTests(unittest.TestCase):
    def test_known_model_can_infer_provider(self) -> None:
        provider = FakeProviderModule()

        with patch("ragrails.models.llm.config.PROVIDERS", {"openai": provider}):
            result = create_llm(LLMConfig(provider="", model="gpt-4.1", max_tokens=123))

        self.assertEqual(result, {"model": "gpt-4.1", "max_tokens": 123})
        self.assertEqual(provider.calls, [{"model": "gpt-4.1", "max_tokens": 123}])

    def test_unknown_model_is_allowed_with_explicit_provider(self) -> None:
        provider = FakeProviderModule()

        with patch("ragrails.models.llm.config.PROVIDERS", {"openai": provider}):
            result = create_llm(LLMConfig(provider="openai", model="gpt-new-custom", max_tokens=500))

        self.assertEqual(result, {"model": "gpt-new-custom", "max_tokens": 500})
        self.assertEqual(provider.calls, [{"model": "gpt-new-custom", "max_tokens": 500}])

    def test_unknown_model_without_provider_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "provide provider explicitly"):
            create_llm(LLMConfig(provider="", model="gpt-new-custom"))

    def test_known_model_rejects_wrong_provider(self) -> None:
        with self.assertRaisesRegex(ValueError, "belongs to provider"):
            create_llm(LLMConfig(provider="anthropic", model="gpt-4.1"))

    def test_unknown_model_cost_is_zero(self) -> None:
        self.assertEqual(_cost("gpt-new-custom", 1_000, 1_000), 0.0)

    def test_catalog_includes_current_openai_models(self) -> None:
        self.assertEqual(get("gpt-5.5").input_price, 5.00)
        self.assertEqual(get("gpt-5.5").output_price, 30.00)
        self.assertEqual(get("gpt-5.4-mini").input_price, 0.75)
        self.assertEqual(get("gpt-5.4-mini").output_price, 4.50)

    def test_catalog_includes_current_anthropic_models(self) -> None:
        self.assertEqual(get("claude-opus-4-8").input_price, 5.00)
        self.assertEqual(get("claude-opus-4-8").output_price, 25.00)
        self.assertEqual(get("claude-sonnet-4-6").input_price, 3.00)
        self.assertEqual(get("claude-sonnet-4-6").output_price, 15.00)

    def test_catalog_includes_google_models(self) -> None:
        self.assertEqual(get("gemini-3-pro").provider, "google")
        self.assertEqual(get("gemini-3-pro").input_price, 2.00)
        self.assertEqual(get("gemini-3-pro").output_price, 12.00)
        self.assertEqual(get("gemini-2.5-flash").input_price, 0.30)
        self.assertEqual(get("gemini-2.5-flash").output_price, 2.50)


if __name__ == "__main__":
    unittest.main()
