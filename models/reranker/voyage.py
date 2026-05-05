import os
from dataclasses import dataclass, field

import voyageai
from dotenv import load_dotenv

from .base import Reranker

load_dotenv()


@dataclass
class VoyageReranker(Reranker):
    model_name: str = "rerank-2-lite"
    _client: voyageai.Client = field(init=False, repr=False, default=None)

    def _get_client(self) -> voyageai.Client:
        if self._client is None:
            api_key = os.environ.get("VOYAGE_API_KEY")
            if not api_key:
                raise ValueError("VOYAGE_API_KEY environment variable not set.")
            self._client = voyageai.Client(api_key=api_key)
        return self._client

    def rerank(self, query: str, texts: list[str]) -> list[float]:
        """Rerank texts against the query using Voyage AI.

        Example:
            model = VoyageReranker()
            scores = model.rerank("How do I transfer funds?", ["Transfer via bank...", "List banks..."])
            # → [0.92, 0.14]  (original order preserved)
        """
        # The reranker is a cross-encoder — it scores each query-document pair together,
        # making it more accurate than the bi-encoder embedder which scores them separately.
        # It's used as a second stage because it's slower and can't scale to the full index,
        # only a smaller pool of candidates already narrowed down by vector search.
        result = self._get_client().rerank(
            query=query,
            documents=texts,
            model=self.model_name,
        )
        # Voyage returns results in relevance order, not input order.
        # We restore the original order so scores align with the input texts by index.
        scores = [0.0] * len(texts)
        for item in result.results:
            scores[item.index] = item.relevance_score
        return scores
