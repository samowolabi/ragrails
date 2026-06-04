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
