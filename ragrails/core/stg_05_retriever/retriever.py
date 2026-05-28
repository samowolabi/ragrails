"""
Retriever — encodes a query, fetches top-k chunks from the vector store,
and optionally re-ranks them with a cross-encoder.
"""

from __future__ import annotations

from ragrails.models.embedder.base import EmbeddingModel
from ragrails.models.llm.base import LLMProvider
from ragrails.models.reranker.base import Reranker
from ragrails.models.vector_db.base import SearchResult, VectorStore

from .config import RetrieverConfig
from .query_rewriter import rewrite


def run_retrieval(
    *,
    query: str,
    model: EmbeddingModel,
    store: VectorStore,
    rewrite_llm: LLMProvider | None = None,
    reranker: Reranker | None = None,
    config: RetrieverConfig | None = None,
    rewrite_context: str = "",
    session_context: str = "",
) -> dict:
    """Run retrieval with optional reranking controlled by RetrieverConfig."""
    cfg = config or RetrieverConfig()
    config_error = _validate_config(cfg)
    if config_error:
        return {"retrieved": 0, "failed": 1, "outputs": [], "errors": [config_error]}

    search_query = query
    rewrite_error = None
    if cfg.use_query_rewrite:
        if rewrite_llm is None:
            return {
                "retrieved": 0,
                "failed": 1,
                "outputs": [],
                "errors": [_failure(source=query, stage="rewrite", error="rewrite_llm is required when use_query_rewrite is True")],
            }
        try:
            search_query = rewrite(
                query,
                llm=rewrite_llm,
                context=rewrite_context,
                session_context=session_context,
            )
        except Exception as e:
            search_query = query
            rewrite_error = _failure(source=query, stage="rewrite", error=str(e), is_retryable=True)

    result = retrieve_results(query=search_query, model=model, store=store, top_k=cfg.top_k)
    result["query"] = query
    result["search_query"] = search_query
    if rewrite_error:
        result["errors"].append(rewrite_error)
        result["failed"] = len(result["errors"])
    if result["errors"] or not cfg.use_rerank:
        return result

    if reranker is None:
        return {
            "retrieved": result["retrieved"],
            "failed": 1,
            "outputs": result["outputs"],
            "errors": [_failure(source=query, stage="rerank", error="reranker is required when use_rerank is True")],
            "query": query,
            "search_query": search_query,
        }

    reranked = rerank_results(
        query=search_query,
        results=result["outputs"],
        model=reranker,
        top_k=cfg.rerank_top_k,
    )
    return {
        "retrieved": result["retrieved"],
        "reranked": reranked["reranked"],
        "failed": reranked["failed"],
        "outputs": reranked["outputs"],
        "errors": reranked["errors"],
        "query": query,
        "search_query": search_query,
    }


def retrieve_results(
    *,
    query: str,
    model: EmbeddingModel,
    store: VectorStore,
    top_k: int = 10,
) -> dict:
    """Encode a query and return structured retrieval results."""
    error = _validate_query(query)
    if error:
        return {"retrieved": 0, "failed": 1, "outputs": [], "errors": [error]}

    error = _validate_top_k(top_k, name="top_k")
    if error:
        return {"retrieved": 0, "failed": 1, "outputs": [], "errors": [error]}

    try:
        vectors = model.encode([query])
        if len(vectors) != 1:
            raise ValueError("embedding model returned a different number of vectors than input queries")
        results = store.search(vectors[0], top_k=top_k)
    except Exception as e:
        return {
            "retrieved": 0,
            "failed": 1,
            "outputs": [],
            "errors": [_failure(source=query, stage="retrieve", error=str(e), is_retryable=True)],
        }

    return {"retrieved": len(results), "failed": 0, "outputs": results, "errors": []}


def retrieve_multi_results(
    *,
    queries: list[str],
    model: EmbeddingModel,
    store: VectorStore,
    top_k_per_query: int = 5,
) -> dict:
    """Retrieve candidates for multiple queries and return structured results."""
    if not isinstance(queries, list) or not queries:
        return {
            "retrieved": 0,
            "failed": 1,
            "outputs": [],
            "errors": [_failure(source="", stage="validate", error="queries must be a non-empty list")],
        }

    error = _validate_top_k(top_k_per_query, name="top_k_per_query")
    if error:
        return {"retrieved": 0, "failed": 1, "outputs": [], "errors": [error]}

    seen_ids: set[str] = set()
    merged: list[SearchResult] = []
    errors = []

    for query in queries:
        result = retrieve_results(query=query, model=model, store=store, top_k=top_k_per_query)
        errors.extend(result["errors"])
        for item in result["outputs"]:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                merged.append(item)

    return {"retrieved": len(merged), "failed": len(errors), "outputs": merged, "errors": errors}


def rerank_results(
    *,
    query: str,
    results: list[SearchResult],
    model: Reranker,
    top_k: int = 5,
) -> dict:
    """Re-rank retrieved results and return structured results."""
    error = _validate_query(query)
    if error:
        return {"reranked": 0, "failed": 1, "outputs": [], "errors": [error]}

    error = _validate_top_k(top_k, name="top_k")
    if error:
        return {"reranked": 0, "failed": 1, "outputs": [], "errors": [error]}

    if not isinstance(results, list):
        return {
            "reranked": 0,
            "failed": 1,
            "outputs": [],
            "errors": [_failure(source=query, stage="validate", error="results must be a list")],
        }

    if not results:
        return {"reranked": 0, "failed": 0, "outputs": [], "errors": []}

    try:
        texts = [r.text for r in results]
        scores = model.rerank(query, texts)
        if len(scores) != len(results):
            raise ValueError("reranker returned a different number of scores than input results")
    except Exception as e:
        return {
            "reranked": 0,
            "failed": len(results),
            "outputs": [],
            "errors": [_failure(source=query, stage="rerank", error=str(e), is_retryable=True)],
        }

    for result, score in zip(results, scores):
        result.rerank_score = score

    outputs = sorted(results, key=lambda r: r.rerank_score, reverse=True)[:top_k]
    return {"reranked": len(outputs), "failed": 0, "outputs": outputs, "errors": []}


def retrieve(
    query: str,
    model: EmbeddingModel,
    store: VectorStore,
    top_k: int = 10,
) -> list[SearchResult]:
    """Compatibility wrapper returning only SearchResult objects."""
    return retrieve_results(query=query, model=model, store=store, top_k=top_k)["outputs"]


def retrieve_multi(
    queries: list[str],
    model: EmbeddingModel,
    store: VectorStore,
    top_k_per_query: int = 5,
) -> list[SearchResult]:
    """Compatibility wrapper returning merged SearchResult objects."""
    return retrieve_multi_results(
        queries=queries,
        model=model,
        store=store,
        top_k_per_query=top_k_per_query,
    )["outputs"]

def rerank(
    query: str,
    results: list[SearchResult],
    model: Reranker,
    top_k: int = 5,
) -> list[SearchResult]:
    """Compatibility wrapper returning only SearchResult objects."""
    return rerank_results(query=query, results=results, model=model, top_k=top_k)["outputs"]


def _validate_query(query: str) -> dict | None:
    if not isinstance(query, str) or not query.strip():
        return _failure(source="", stage="validate", error="query must be a non-empty string")
    return None


def _validate_config(config: RetrieverConfig) -> dict | None:
    if not isinstance(config.use_query_rewrite, bool):
        return _failure(source="", stage="validate", error="use_query_rewrite must be a boolean")
    if not isinstance(config.use_rerank, bool):
        return _failure(source="", stage="validate", error="use_rerank must be a boolean")
    top_k_error = _validate_top_k(config.top_k, name="top_k")
    if top_k_error:
        return top_k_error
    rerank_top_k_error = _validate_top_k(config.rerank_top_k, name="rerank_top_k")
    if rerank_top_k_error:
        return rerank_top_k_error
    return None


def _validate_top_k(top_k: int, *, name: str) -> dict | None:
    if isinstance(top_k, bool) or not isinstance(top_k, int):
        return _failure(source="", stage="validate", error=f"{name} must be an integer")
    if top_k < 1:
        return _failure(source="", stage="validate", error=f"{name} must be greater than 0")
    return None


def _failure(
    *,
    source: str,
    stage: str,
    error: str,
    is_retryable: bool = False,
) -> dict:
    return {
        "source": source,
        "source_kind": "query",
        "stage": stage,
        "error": error,
        "isRetryable": is_retryable,
        "attempts": 1,
    }


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
