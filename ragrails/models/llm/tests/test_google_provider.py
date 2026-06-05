from __future__ import annotations

import unittest
from unittest.mock import Mock

from ragrails.models.llm.providers import PROVIDERS
from ragrails.models.llm.providers.google import GoogleProvider


class FakeUsage:
    prompt_token_count = 11
    candidates_token_count = 7


class FakeResponse:
    text = "Gemini answer"
    usage_metadata = FakeUsage()


class FakeModels:
    def __init__(self) -> None:
        self.generate_content = Mock(return_value=FakeResponse())
        self.generate_content_stream = Mock(return_value=[Mock(text="A"), Mock(text="B")])


class FakeClient:
    def __init__(self) -> None:
        self.models = FakeModels()


class GoogleProviderTests(unittest.TestCase):
    def test_google_provider_is_registered(self) -> None:
        self.assertIn("google", PROVIDERS)

    def test_complete_maps_request_and_response(self) -> None:
        client = FakeClient()
        provider = GoogleProvider(model="gemini-3-pro", max_tokens=256)
        provider._client = client

        response = provider.complete(
            system="You are helpful.",
            user="Hello",
            history=[{"role": "assistant", "content": "Previous answer"}],
            temperature=0.2,
        )

        call = client.models.generate_content.call_args.kwargs
        self.assertEqual(call["model"], "gemini-3-pro")
        self.assertEqual(call["contents"][0]["role"], "model")
        self.assertEqual(call["contents"][1]["role"], "user")
        self.assertEqual(call["config"]["system_instruction"], "You are helpful.")
        self.assertEqual(call["config"]["max_output_tokens"], 256)
        self.assertEqual(call["config"]["temperature"], 0.2)
        self.assertEqual(response.text, "Gemini answer")
        self.assertEqual(response.input_tokens, 11)
        self.assertEqual(response.output_tokens, 7)
        self.assertEqual(response.provider, "google")

    def test_stream_yields_text_chunks(self) -> None:
        client = FakeClient()
        provider = GoogleProvider(model="gemini-2.5-flash", max_tokens=128)
        provider._client = client

        self.assertEqual(list(provider.stream("System", "User")), ["A", "B"])

    def test_tool_calling_is_explicitly_not_implemented(self) -> None:
        provider = GoogleProvider(model="gemini-3-pro", max_tokens=256)

        with self.assertRaisesRegex(NotImplementedError, "tool calling"):
            provider.complete_with_tools(messages=[], system="System", tools=[{"name": "lookup"}])


if __name__ == "__main__":
    unittest.main()
