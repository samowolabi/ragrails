from dataclasses import dataclass, field

from .quality import RetrievalQualityConfig


@dataclass
class ChatConfig:
    persona: str = ""
    use_intent_routing: bool = True
    retrieval_quality: RetrievalQualityConfig = field(default_factory=RetrievalQualityConfig)
