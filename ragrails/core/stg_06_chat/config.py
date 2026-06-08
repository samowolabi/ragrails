from dataclasses import dataclass, field

from .quality import RetrievalQualityConfig


@dataclass
class QueryRewriteConfig:
    enabled: bool = False
    llm: object | None = None
    context: str = ""
    session_context: str = ""


@dataclass
class ChatConfig:
    persona: str = ""
    use_intent_routing: bool = True
    retrieval_quality: RetrievalQualityConfig = field(default_factory=RetrievalQualityConfig)
    rewrite_query: bool = False
    use_tools: bool = True
    stream: bool = False
    history_limit: int | None = 15

    @property
    def min_retrieval_score(self) -> float:
        return self.retrieval_quality.min_retrieval_score

    @property
    def min_rerank_score(self) -> float:
        return self.retrieval_quality.min_rerank_score
