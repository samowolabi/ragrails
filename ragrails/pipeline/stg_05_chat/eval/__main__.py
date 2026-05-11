"""Run end-to-end RAG quality evaluation.

Examples:
    uv run python -m ragrails.pipeline.stg_05_chat.eval
    uv run python -m ragrails.pipeline.stg_05_chat.eval --golden files/eval/rag_golden.jsonl
    uv run python -m ragrails.pipeline.stg_05_chat.eval --retrieval-only
    uv run python -m ragrails.pipeline.stg_05_chat.eval --judge
    uv run python -m ragrails.pipeline.stg_05_chat.eval \
        --collection opencode_rag_chunks \
        --golden files/eval/opencode_rag_golden.jsonl \
        --rewrite-context "OpenCode documentation" \
        --judge
"""

from __future__ import annotations

import argparse
import sys

from ragrails.config.settings import Settings
from ragrails.models.embedder.config import EmbedderConfig, create_embedder
from ragrails.models.llm.config import LLMConfig, create_llm
from ragrails.models.reranker.config import RerankerConfig, create_reranker
from ragrails.models.vector_db.registry import create_vector_store
from ragrails.pipeline.stg_04_retriever.config import RetrieverConfig
from ragrails.pipeline.stg_04_retriever.query_rewriter import rewrite
from ragrails.pipeline.stg_04_retriever.retriever import rerank, retrieve
from ragrails.pipeline.stg_05_chat.config import ChatConfig
from ragrails.pipeline.stg_05_chat.generator import generate

from .metrics import (
    EvalCase,
    EvalResult,
    citations_are_valid,
    judge_answer,
    load_cases,
    quality_score,
    required_term_metrics,
    retrieval_metrics,
)

W = 72

_COLORS = [
    (90, "\033[38;2;88;198;138m"),
    (80, "\033[32m"),
    (70, "\033[33m"),
    (55, "\033[31m"),
    (0, "\033[91m"),
]
_RESET = "\033[0m"


def main() -> None:
    args = _parse_args()
    cases = load_cases(args.golden)
    if not cases:
        print(f"No eval cases found in {args.golden}")
        sys.exit(1)

    settings = Settings()
    llm = create_llm(LLMConfig(provider=args.provider, model=args.model))
    embedder = create_embedder(EmbedderConfig(), input_type="query")
    reranker = create_reranker(RerankerConfig())
    store = create_vector_store(
        provider=settings.vector_db_provider,
        url=settings.vector_db_url,
        collection=args.collection or settings.collection,
    )
    retriever_cfg = RetrieverConfig(top_k=args.top_k)
    chat_cfg = ChatConfig(
        persona=args.persona,
        min_rerank_score=args.min_rerank_score,
        min_retrieval_score=args.min_retrieval_score,
        rewrite_query=not args.no_rewrite,
        use_tools=False,
    )

    print(f"\n{'═' * W}")
    print("  RAG EVAL")
    print(f"  cases={len(cases)}  vector_db={store.provider}/{store.collection}  model={args.provider}/{args.model}  judge={'on' if args.judge else 'off'}")
    print(f"{'═' * W}")

    results = []
    for idx, case in enumerate(cases, start=1):
        print(f"\n  [{idx}/{len(cases)}] {case.id}: {case.question}")
        try:
            results.append(_run_case(
                case=case,
                llm=llm,
                embedder=embedder,
                reranker=reranker,
                store=store,
                retriever_cfg=retriever_cfg,
                chat_cfg=chat_cfg,
                rewrite_context=args.rewrite_context,
                retrieval_only=args.retrieval_only,
                judge=args.judge,
            ))
        except Exception as e:
            results.append(EvalResult(
                case=case,
                rewritten_query=case.question,
                ranked=[],
                used_sources=[],
                citations_valid=False,
                error=str(e),
            ))
        _print_case(results[-1])

    _print_summary(results)


def _run_case(
    case: EvalCase,
    llm,
    embedder,
    reranker,
    store,
    retriever_cfg: RetrieverConfig,
    chat_cfg: ChatConfig,
    rewrite_context: str,
    retrieval_only: bool,
    judge: bool,
) -> EvalResult:
    query = case.question
    if chat_cfg.rewrite_query:
        try:
            query = rewrite(case.question, llm=llm, context=rewrite_context)
        except Exception as e:
            print(f"    rewrite failed: {e}")
            query = case.question

    candidates = retrieve(
        query,
        model=embedder,
        store=store,
        top_k=max(retriever_cfg.top_k * 2, 20),
    )
    ranked = []
    if max((c.score for c in candidates), default=0) >= chat_cfg.min_retrieval_score:
        ranked = rerank(query, candidates, model=reranker, top_k=retriever_cfg.top_k)

    hit, top1, rr = retrieval_metrics(case, ranked)
    result = EvalResult(
        case=case,
        rewritten_query=query,
        ranked=ranked,
        used_sources=[],
        retrieval_hit=hit,
        top1_hit=top1,
        reciprocal_rank=rr,
    )

    if retrieval_only:
        return result

    response = generate(case.question, ranked, llm=llm, config=chat_cfg, history=[])
    found, missing = required_term_metrics(response.answer, case.required_terms)
    result.answer = response.answer
    result.used_sources = response.sources
    result.required_terms_found = found
    result.required_terms_missing = missing
    result.citations_valid = citations_are_valid(response.answer, response.sources)

    if judge:
        result.judge = judge_answer(case, response.answer, ranked, llm)

    return result


def _print_case(result: EvalResult) -> None:
    score = result.overall_score
    print(f"    score:      {_color(score, f'{score:.1f}/100')}")
    if result.error:
        print(f"    error:      {result.error}")
        return
    if result.rewritten_query != result.case.question:
        print(f"    rewritten:  {result.rewritten_query}")
    print(f"    retrieval:  hit={_yes(result.retrieval_hit)} top1={_yes(result.top1_hit)} mrr={result.reciprocal_rank:.3f}")
    if result.case.required_terms:
        missing = ", ".join(result.required_terms_missing) if result.required_terms_missing else "none"
        print(f"    terms:      found={len(result.required_terms_found)}/{len(result.case.required_terms)} missing={missing}")
    if result.answer:
        print(f"    citations:  {_yes(result.citations_valid)}")
    if result.judge:
        print(
            f"    judge:      {result.judge.score:.1f}/100 "
            f"faith={result.judge.faithfulness:.0f} rel={result.judge.relevance:.0f} comp={result.judge.completeness:.0f}"
        )
        if result.judge.explanation:
            print(f"    judge note: {result.judge.explanation}")
    if result.ranked:
        top = result.ranked[0]
        print(f"    top source: {top.metadata.get('title', '')}  {top.metadata.get('path', '')}")


def _print_summary(results: list[EvalResult]) -> None:
    score, grade = quality_score(results)
    hits = sum(1 for r in results if r.retrieval_hit)
    top1 = sum(1 for r in results if r.top1_hit)
    citations = sum(1 for r in results if r.citations_valid)
    mean_mrr = sum(r.reciprocal_rank for r in results) / len(results) if results else 0

    print(f"\n{'─' * W}")
    print(f"  Quality score      {_color(score, f'{score:.1f}/100 {grade}')}")
    print(f"  Retrieval hit      {hits}/{len(results)}")
    print(f"  Top-1 hit          {top1}/{len(results)}")
    print(f"  Mean reciprocal    {mean_mrr:.3f}")
    print(f"  Valid citations    {citations}/{len(results)}")
    print(f"{'═' * W}\n")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate end-to-end RAG quality.")
    parser.add_argument("--golden", default="files/eval/opencode_rag_golden.jsonl", help="JSONL golden eval file")
    parser.add_argument("--collection", default="", help="Vector DB collection name. Defaults to config.settings.Settings.collection")
    parser.add_argument("--provider", default="openai", help="LLM provider for rewrite/generation/judge")
    parser.add_argument("--model", default="gpt-4o", help="LLM model for rewrite/generation/judge")
    parser.add_argument("--top-k", type=int, default=10, help="Final reranked top-k")
    parser.add_argument("--min-retrieval-score", type=float, default=0.40)
    parser.add_argument("--min-rerank-score", type=float, default=0.50)
    parser.add_argument("--persona", default="You are a helpful documentation assistant.")
    parser.add_argument("--rewrite-context", default="", help="Optional domain hint for query rewriting, e.g. 'OpenCode documentation'")
    parser.add_argument("--no-rewrite", action="store_true", help="Evaluate retrieval without query rewriting")
    parser.add_argument("--retrieval-only", action="store_true", help="Skip answer generation and judge scoring")
    parser.add_argument("--judge", action="store_true", help="Use an LLM judge for answer quality")
    return parser.parse_args()


def _color(score: float, text: str) -> str:
    code = next(c for threshold, c in _COLORS if score >= threshold)
    return f"{code}{text}{_RESET}"


def _yes(value: bool) -> str:
    return "yes" if value else "no"


if __name__ == "__main__":
    main()
