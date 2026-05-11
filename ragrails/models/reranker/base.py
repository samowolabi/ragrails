from abc import ABC, abstractmethod


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, texts: list[str]) -> list[float]:
        """Return a relevance score in [0, 1] for each (query, text) pair.

        Output order matches input order — higher score means more relevant.

        Example:
            model = VoyageReranker()
            scores = model.rerank("How do I transfer funds?", ["Transfer via bank...", "List all banks..."])
            # → [0.92, 0.14]
        """
        ...
