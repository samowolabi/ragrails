from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from ragrails.interfaces.server.app import create_app


class ServerChatRouteTests(unittest.TestCase):
    def test_chat_stream_returns_sse_events(self) -> None:
        client = TestClient(create_app())
        events = [
            {"type": "progress", "stage": "retrieval", "message": "Started", "data": {}, "sequence": 1},
            {"type": "token", "stage": "generation", "message": "", "data": {"text": "Hi"}, "sequence": 2},
            {"type": "final", "stage": "complete", "message": "Done", "data": {"answer": "Hi"}, "sequence": 3},
        ]

        with patch("ragrails.interfaces.server.chat.services.run_chat_stream", return_value=iter(events)):
            response = client.post("/v1/chat/stream", json={"query": "hello"})

        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("text/event-stream", response.headers["content-type"])
        self.assertIn("event: token", response.text)
        self.assertIn('"text": "Hi"', response.text)
        self.assertIn("event: final", response.text)


if __name__ == "__main__":
    unittest.main()
