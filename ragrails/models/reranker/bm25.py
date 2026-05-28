from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .base import Reranker


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass
class BM25Reranker(Reranker):
    model_name: str = "bm25"
    k1: float = 1.5
    b: float = 0.75

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        """Score texts with BM25 and return scores in input order."""
        if not texts:
            return []

        query_terms = _tokenize(query)
        if not query_terms:
            return [0.0 for _ in texts]

        documents = [_tokenize(text) for text in texts]
        average_length = sum(len(doc) for doc in documents) / len(documents)
        document_frequencies = _document_frequencies(documents)

        raw_scores = [
            self._score_document(
                query_terms=query_terms,
                document_terms=document_terms,
                document_frequencies=document_frequencies,
                document_count=len(documents),
                average_length=average_length,
            )
            for document_terms in documents
        ]
        return _normalize(raw_scores)

    def _score_document(
        self,
        *,
        query_terms: list[str],
        document_terms: list[str],
        document_frequencies: dict[str, int],
        document_count: int,
        average_length: float,
    ) -> float:
        if not document_terms:
            return 0.0

        term_counts = Counter(document_terms)
        document_length = len(document_terms)
        score = 0.0

        for term in query_terms:
            frequency = term_counts.get(term, 0)
            if frequency == 0:
                continue

            df = document_frequencies.get(term, 0)
            idf = math.log(1 + (document_count - df + 0.5) / (df + 0.5))
            denominator = frequency + self.k1 * (1 - self.b + self.b * document_length / average_length)
            score += idf * (frequency * (self.k1 + 1)) / denominator

        return score


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(text or "")]


def _document_frequencies(documents: list[list[str]]) -> dict[str, int]:
    frequencies: dict[str, int] = {}
    for terms in documents:
        for term in set(terms):
            frequencies[term] = frequencies.get(term, 0) + 1
    return frequencies


def _normalize(scores: list[float]) -> list[float]:
    max_score = max(scores, default=0.0)
    if max_score <= 0:
        return [0.0 for _ in scores]
    return [score / max_score for score in scores]
