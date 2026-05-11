import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


load_dotenv()


@dataclass
class Settings:
    # Vector store
    vector_db_provider: str = field(default_factory=lambda: os.environ.get("VECTOR_DB_PROVIDER", "qdrant"))
    vector_db_url: str = field(default_factory=lambda: os.environ.get("VECTOR_DB_URL", ""))
    collection: str = field(default_factory=lambda: os.environ.get("VECTOR_DB_COLLECTION", ""))

    def __post_init__(self) -> None:
        self.vector_db_provider = self.vector_db_provider.lower().strip()
        if not self.collection:
            if self.vector_db_provider == "pinecone":
                self.collection = "rag-chunks"
            elif self.vector_db_provider == "weaviate":
                self.collection = "RagChunks"
            else:
                self.collection = "opencode_rag_chunks"
