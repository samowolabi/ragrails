from dataclasses import dataclass


@dataclass
class Settings:
    # Qdrant vector store
    qdrant_url: str = "http://localhost:6333"
    collection: str = "opencode_rag_chunks"
