"""
Retriever — encodes a query, fetches top-k chunks from the vector store,
and optionally re-ranks them with a cross-encoder.
"""

from models.embedder.base import EmbeddingModel
from models.reranker.base import Reranker
from models.vector_db.base import SearchResult, VectorStore


def retrieve(
    query: str,
    model: EmbeddingModel,
    store: VectorStore,
    top_k: int = 10,
) -> list[SearchResult]:
    """Encode query and return the top-k nearest chunks from the store.

    Example:
        results = retrieve("How do I transfer funds?", model=embed_model, store=store, top_k=10)
        # → [SearchResult(id="abc-123", score=0.94, text="...", metadata={...}), ...]
    """
    # The model must be initialized with input_type="query" so Voyage produces
    # query-optimized embeddings — different from the "document" embeddings stored at index time.
    query_vector = model.encode([query])[0]
    return store.search(query_vector, top_k=top_k)


def retrieve_multi(
    queries: list[str],
    model: EmbeddingModel,
    store: VectorStore,
    top_k_per_query: int = 5,
) -> list[SearchResult]:
    """Retrieve candidates for multiple sub-queries and merge, deduplicating by chunk id.

    Example:
        results = retrieve_multi(["transfer funds", "bank transfer fees"], model=embed_model, store=store)
    """
    # A single query may not capture all relevant chunks if the question has multiple angles.
    # Running retrieval across multiple sub-queries broadens coverage.
    # Deduplication by id ensures the same chunk isn't passed to the reranker twice.
    seen_ids: set[str] = set()
    merged: list[SearchResult] = []

    for query in queries:
        for r in retrieve(query, model=model, store=store, top_k=top_k_per_query):
            if r.id not in seen_ids:
                seen_ids.add(r.id)
                merged.append(r)

    return merged


def rerank(
    query: str,
    results: list[SearchResult],
    model: Reranker,
    top_k: int = 5,
) -> list[SearchResult]:
    """Re-rank retrieved results using a cross-encoder and return the top_k.

    Example:
        final = rerank("How do I transfer funds?", candidates, model=rerank_model, top_k=5)
        # → top 5 SearchResult objects sorted by rerank_score descending
    """
    if not results:
        return []

    # Two-stage retrieval strategy:
    # Stage 1 (retrieve) — fast bi-encoder vector search across the full index.
    # Stage 2 (here) — slower cross-encoder reranker on the narrowed candidate pool.
    # This balances speed and accuracy: vector search is fast but approximate,
    # the cross-encoder is more precise but too slow to run on the full index.
    texts = [r.text for r in results]
    scores = model.rerank(query, texts)

    for result, score in zip(results, scores):
        result.rerank_score = score

    return sorted(results, key=lambda r: r.rerank_score, reverse=True)[:top_k]


def print_results(results: list[SearchResult]) -> None:
    """Pretty-print retrieval results to stdout."""
    if not results:
        print("No results found.")
        return

    for i, r in enumerate(results, start=1):
        title        = r.metadata.get("title", "")
        path         = r.metadata.get("path", "")
        heading      = r.metadata.get("heading", {})
        heading_text = " > ".join(heading.values()) if isinstance(heading, dict) else str(heading)

        score_str = f"retrieval={r.score:.4f}"
        if r.rerank_score is not None:
            score_str += f"  rerank={r.rerank_score:.4f}"

        print(f"\n{'─' * 60}")
        print(f"[{i}]  {score_str}  id={r.id}")
        if title:
            print(f"     title:   {title}")
        if heading_text:
            print(f"     heading: {heading_text}")
        if path:
            print(f"     path:    {path}")
        print(f"\n{r.text[:400]}{'…' if len(r.text) > 400 else ''}")

    print(f"\n{'─' * 60}")
