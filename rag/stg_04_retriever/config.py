from dataclasses import dataclass


@dataclass
class RetrieverConfig:
    top_k:            int   = 10
    min_rerank_score: float = 0.5
