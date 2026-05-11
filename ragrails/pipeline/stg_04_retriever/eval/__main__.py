"""
Run:
    uv run python -m ragrails.pipeline.stg_04_retriever.eval                  # eval 10 auto-generated queries
    uv run python -m ragrails.pipeline.stg_04_retriever.eval <n>              # eval n auto-generated queries
    uv run python -m ragrails.pipeline.stg_04_retriever.eval query "<query>"  # eval a single query directly
"""

import json
import random
import sys
from pathlib import Path

from ragrails.models.llm.config import LLMConfig, create_llm

from ..config import RetrieverConfig
from ..query_rewriter import rewrite
from .metrics import RewriteResult, generate_question, quality_score, score_rewrite

W = 60

_COLORS = [
    (90, "\033[38;2;88;198;138m"),  # #58C68A — Excellent
    (75, "\033[32m"),               # green   — Good
    (60, "\033[33m"),               # yellow  — Fair
    (40, "\033[31m"),               # red     — Poor
    (0,  "\033[91m"),               # bright red — Critical
]
_RESET = "\033[0m"


def _color(score: float, text: str) -> str:
    code = next(c for threshold, c in _COLORS if score >= threshold)
    return f"{code}{text}{_RESET}"


def _load_chunks(chunks_dir: str, sample_n: int, seed: int = 42) -> list[dict]:
    paths = sorted(Path(chunks_dir).glob("*.json"))
    all_chunks: list[dict] = []
    for p in paths:
        all_chunks.extend(json.load(open(p)))
    rng = random.Random(seed)
    return rng.sample(all_chunks, min(sample_n, len(all_chunks)))


def _print_result(r: RewriteResult, idx: int) -> None:
    print(f"\n  [{idx}] {_color(r.score, f'{r.score:.1f}/100')}")
    print(f"  Original:  {r.original}")
    print(f"  Rewritten: {r.rewritten}")
    print(f"  Specificity={r.specificity:.0f}  Intent={r.intent:.0f}  Expansion={r.expansion:.0f}")


def _print_report(results: list[RewriteResult], title: str) -> None:
    score, grade = quality_score(results)
    passed = sum(1 for r in results if r.score >= 75)
    warned = sum(1 for r in results if 60 <= r.score < 75)
    failed = sum(1 for r in results if r.score < 60)

    print(f"\n{'═' * W}")
    print(f"  {title}")
    print(f"  {len(results)} rewrite(s) evaluated")
    print(f"{'═' * W}")
    for i, r in enumerate(results, start=1):
        _print_result(r, i)
    print(f"\n{'─' * W}")
    print(f"  {'Quality score':<26} {_color(score, f'{score} / 100     {grade}')}")
    print(f"  {'Result':<26} {passed} pass · {warned} warn · {failed} fail")
    print(f"{'═' * W}\n")


llm = create_llm(LLMConfig(provider="openai", model="gpt-4o-mini"))
cfg = RetrieverConfig()
mode = sys.argv[1] if len(sys.argv) > 1 else "auto"

if mode == "query":
    if len(sys.argv) < 3:
        print("Usage: uv run python -m ragrails.pipeline.stg_04_retriever.eval query \"<query>\"")
        sys.exit(1)

    original  = sys.argv[2]
    rewritten = rewrite(original, llm=llm)
    result    = score_rewrite(original, rewritten, llm=llm)
    _print_report([result], "REWRITE EVAL — SINGLE QUERY")

else:
    sample_n = int(mode) if mode.isdigit() else 10
    chunks_dir = "files/output/chunks"

    print(f"\nGenerating {sample_n} questions from sampled chunks…")
    chunks = _load_chunks(chunks_dir, sample_n)

    results: list[RewriteResult] = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"  [{i}/{sample_n}] generating question…")
        original  = generate_question(chunk, llm=llm)
        rewritten = rewrite(original, llm=llm)
        result    = score_rewrite(original, rewritten, llm=llm)
        results.append(result)

    _print_report(results, f"REWRITE EVAL — {sample_n} AUTO-GENERATED QUERIES")
