from dataclasses import dataclass


@dataclass
class RetrieverConfig:
    top_k: int = 10
    use_query_rewrite: bool = False
    use_rerank: bool = False
    rerank_top_k: int = 5
    min_rerank_score: float = 0.5
