from abc import ABC, abstractmethod


class EmbeddingModel(ABC):
    @abstractmethod
    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode a batch of texts into dense vectors.

        Example:
            model = VoyageModel()
            vectors = model.encode(["Transfer funds via bank transfer", "List all banks"])
            # → [[0.021, -0.043, ...], [0.017, 0.082, ...]]  (512-dim each)
        """
        ...

    @property
    @abstractmethod
    def vector_size(self) -> int:
        """Dimensionality of the output vectors.

        Example:
            VoyageModel().vector_size  # → 512
        """
        ...
