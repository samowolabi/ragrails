from __future__ import annotations

import unittest

from ragrails.models.reranker.bm25 import BM25Reranker
from ragrails.models.reranker.config import RerankerConfig, create_reranker


class BM25RerankerTests(unittest.TestCase):
    def test_scores_matching_documents_higher(self) -> None:
        model = BM25Reranker()

        scores = model.rerank(
            "bank transfer fees",
            [
                "Card payment webhook events",
                "Bank transfer fees and settlement timing",
                "Identity verification requirements",
            ],
        )

        self.assertEqual(len(scores), 3)
        self.assertEqual(scores[1], 1.0)
        self.assertGreater(scores[1], scores[0])
        self.assertGreater(scores[1], scores[2])

    def test_returns_zero_scores_for_empty_query(self) -> None:
        scores = BM25Reranker().rerank("", ["one", "two"])

        self.assertEqual(scores, [0.0, 0.0])

    def test_returns_empty_scores_for_empty_texts(self) -> None:
        scores = BM25Reranker().rerank("query", [])

        self.assertEqual(scores, [])

    def test_create_reranker_can_create_bm25(self) -> None:
        model = create_reranker(RerankerConfig(provider="bm25", model="bm25"))

        self.assertIsInstance(model, BM25Reranker)

    def test_options_are_passed_to_bm25(self) -> None:
        model = create_reranker(
            RerankerConfig(
                provider="bm25",
                model="bm25",
                options={"k1": 1.2, "b": 0.5},
            )
        )

        self.assertEqual(model.k1, 1.2)
        self.assertEqual(model.b, 0.5)


if __name__ == "__main__":
    unittest.main()
