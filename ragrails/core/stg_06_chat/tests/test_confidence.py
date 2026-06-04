from __future__ import annotations

import unittest

from ragrails.core.stg_06_chat.confidence import build_answer_confidence


class ConfidenceTests(unittest.TestCase):
    def test_high_confidence_when_multiple_strong_sources_pass(self) -> None:
        result = build_answer_confidence(
            retrieval_quality={"status": "pass", "passed_chunks": 2},
            sources=[
                {"retrieval_score": 0.8, "rerank_score": None},
                {"retrieval_score": 0.7, "rerank_score": None},
            ],
            intent="rag",
            errors=[],
        )

        self.assertEqual(result["level"], "high")
        self.assertEqual(result["reason"], "retrieval_quality_pass")
        self.assertEqual(result["signals"]["best_retrieval_score"], 0.8)

    def test_medium_confidence_when_one_source_passes(self) -> None:
        result = build_answer_confidence(
            retrieval_quality={"status": "pass", "passed_chunks": 1},
            sources=[{"retrieval_score": 0.6, "rerank_score": None}],
            intent="rag",
            errors=[],
        )

        self.assertEqual(result["level"], "medium")

    def test_low_confidence_metadata(self) -> None:
        result = build_answer_confidence(
            retrieval_quality={"status": "low_confidence", "mode": "answer_with_caution", "passed_chunks": 0},
            sources=[],
            intent="rag",
            errors=[],
        )

        self.assertEqual(result["level"], "low")
        self.assertEqual(result["reason"], "low_confidence:answer_with_caution")

    def test_error_confidence_metadata(self) -> None:
        result = build_answer_confidence(
            retrieval_quality={"status": "not_evaluated"},
            sources=[],
            intent="rag",
            errors=[{"stage": "quality"}],
        )

        self.assertEqual(result["level"], "none")
        self.assertEqual(result["reason"], "errors")


if __name__ == "__main__":
    unittest.main()
