from __future__ import annotations

import unittest

from ragrails.core.stg_06_chat.intent import (
    ACKNOWLEDGEMENT_INTENT,
    FAREWELL_INTENT,
    GREETING_INTENT,
    RAG_INTENT,
    THANKS_INTENT,
    detect_intent,
    should_bypass_retrieval,
)


class IntentTests(unittest.TestCase):
    def test_detects_small_talk_intents(self) -> None:
        cases = {
            "hello": GREETING_INTENT,
            "how are you?": GREETING_INTENT,
            "thank you": THANKS_INTENT,
            "appreciate it": THANKS_INTENT,
            "bye": FAREWELL_INTENT,
            "got it": ACKNOWLEDGEMENT_INTENT,
            "sounds good": ACKNOWLEDGEMENT_INTENT,
        }

        for message, intent in cases.items():
            with self.subTest(message=message):
                self.assertEqual(detect_intent(message), intent)
                self.assertTrue(should_bypass_retrieval(intent))

    def test_detects_rag_intent_for_substantive_questions(self) -> None:
        self.assertEqual(detect_intent("how do I authenticate?"), RAG_INTENT)
        self.assertEqual(detect_intent("thanks, now how do I create a payout?"), RAG_INTENT)
        self.assertFalse(should_bypass_retrieval(RAG_INTENT))


if __name__ == "__main__":
    unittest.main()
