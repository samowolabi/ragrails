"""
Run:
    uv run python -m ragrails.pipeline.stg_04_retriever "<query>"
    uv run python -m ragrails.pipeline.stg_04_retriever "<query>" --no-rewrite   # skip query rewriting
    uv run python -m ragrails.pipeline.stg_04_retriever "<query>" --top-k 5      # default 10
"""

import sys

from ragrails.config.settings import Settings
from ragrails.models.embedder.config import EmbedderConfig, create_embedder
from ragrails.models.reranker.config import RerankerConfig, create_reranker
from ragrails.models.llm.config import LLMConfig, create_llm
from ragrails.models.vector_db.registry import create_vector_store

from .config import RetrieverConfig
from .query_rewriter import rewrite
from .retriever import print_results, rerank, retrieve

if len(sys.argv) < 2:
    print("Usage: uv run python -m ragrails.pipeline.stg_04_retriever \"<query>\" [--no-rewrite] [--top-k N]")
    sys.exit(1)

query      = sys.argv[1]
no_rewrite = "--no-rewrite" in sys.argv
top_k      = int(sys.argv[sys.argv.index("--top-k") + 1]) if "--top-k" in sys.argv else 10

settings         = Settings()
retriever_config = RetrieverConfig()
embedder         = create_embedder(EmbedderConfig(), input_type="query")
reranker         = create_reranker(RerankerConfig())
llm              = create_llm(LLMConfig())
vector_store     = create_vector_store(
    provider=settings.vector_db_provider,
    url=settings.vector_db_url,
    collection=settings.collection,
)

print(f"\nQuery: {query}")

if no_rewrite:
    search_query = query
else:
    search_query = rewrite(query, llm=llm)

# fetch at least 2× top_k candidates so reranking has room to work
num_candidates = max(retriever_config.top_k, top_k * 2)
candidates     = retrieve(search_query, model=embedder, store=vector_store, top_k=num_candidates)
results        = rerank(search_query, candidates, model=reranker, top_k=top_k)

print_results(results)
