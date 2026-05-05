import os
from dataclasses import dataclass, field

import voyageai
from dotenv import load_dotenv

from .base import EmbeddingModel

load_dotenv()


@dataclass
class VoyageModel(EmbeddingModel):
    model_name: str = "voyage-3"
    batch_size: int = 128
    # Voyage optimizes embeddings differently depending on the role:
    # "document" at index time produces embeddings suited for being retrieved.
    # "query" at retrieval time produces embeddings suited for matching against documents.
    # Using the wrong type degrades retrieval quality.
    input_type: str = "document"
    _client: voyageai.Client | None = field(init=False, repr=False, default=None)

    _VECTOR_SIZES: dict[str, int] = field(init=False, repr=False, default_factory=lambda: {
        "voyage-3-lite":  512,
        "voyage-3":      1024,
        "voyage-3-large": 1024,
    })

    @property
    def vector_size(self) -> int:
        """Return output dimensions for the selected model.

        Example:
            VoyageModel("voyage-3").vector_size       # → 1024
            VoyageModel("voyage-3-lite").vector_size  # → 512
        """
        return self._VECTOR_SIZES.get(self.model_name, 1024)

    def _get_client(self) -> voyageai.Client:
        if self._client is None:
            api_key = os.environ.get("VOYAGE_API_KEY")
            if not api_key:
                raise ValueError("VOYAGE_API_KEY environment variable not set.")
            self._client = voyageai.Client(api_key=api_key)
        return self._client

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode texts in batches and return all vectors.

        Example:
            model = VoyageModel(input_type="query")
            vectors = model.encode(["How do I initiate a bank transfer?"])
            # → [[0.021, -0.043, ...]]  (512-dim)
        """
        # Voyage has a per-request limit, so large inputs are split into batches.
        # All batches use the same input_type, keeping embeddings consistent.
        client = self._get_client()
        all_embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i: i + self.batch_size]
            result = client.embed(batch, model=self.model_name, input_type=self.input_type)
            all_embeddings.extend(result.embeddings)
        return all_embeddings
