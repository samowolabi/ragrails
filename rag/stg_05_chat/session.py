"""
ChatSession — owns all mutable state for one chat session.

Built once at startup, mutated by the REPL loop and slash commands.
Replaces the scattered globals that previously lived in __main__.py.
"""

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field

from config.settings import Settings
from models.embedder.base import EmbeddingModel
from models.embedder.config import EmbedderConfig, create_embedder
from models.llm.base import History, LLMProvider
from models.llm.config import LLMConfig, create_llm
from models.reranker.base import Reranker
from models.reranker.config import RerankerConfig, create_reranker
from models.vector_db.base import VectorStore
from models.vector_db.qdrant import QdrantStore
from rag.stg_04_retriever.config import RetrieverConfig

from .config import ChatConfig
from .debug_trace import RagDebugTrace


@dataclass
class ChatSession:
    """Mutable state shared across the REPL, pipeline, and slash commands."""

    # Configs
    chat_config:      ChatConfig
    llm_config:       LLMConfig
    retriever_config: RetrieverConfig

    # Models / stores
    llm:          LLMProvider
    embedder:     EmbeddingModel
    reranker:     Reranker
    vector_store: VectorStore

    # Conversation state
    history:         History = field(default_factory=list)
    session_context: str     = ""
    debug_trace:     RagDebugTrace | None = None

    # Background tasks (history summarization + session context update)
    executor:        ThreadPoolExecutor = field(default_factory=lambda: ThreadPoolExecutor(max_workers=2))
    pending_summary: Future | None      = None
    pending_context: Future | None      = None

    def shutdown(self) -> None:
        """Stop the background executor — call on exit."""
        self.executor.shutdown(wait=False)


def build_session(chat_config: ChatConfig | None = None) -> ChatSession:
    """Wire up all dependencies and return a ready-to-use ChatSession.

    Example:
        session = build_session(ChatConfig(persona="You are an Acme assistant."))
    """
    settings = Settings()
    chat     = chat_config or ChatConfig()
    llm_cfg  = LLMConfig()
    ret_cfg  = RetrieverConfig()

    return ChatSession(
        chat_config      = chat,
        llm_config       = llm_cfg,
        retriever_config = ret_cfg,
        llm              = create_llm(llm_cfg),
        embedder         = create_embedder(EmbedderConfig(), input_type="query"),
        reranker         = create_reranker(RerankerConfig()),
        vector_store     = QdrantStore(url=settings.qdrant_url, collection=settings.collection),
    )
