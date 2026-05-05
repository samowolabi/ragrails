"""
Run:
    uv run python -m rag.stg_02_chunker.eval                        # structural eval — all chunk files
    uv run python -m rag.stg_02_chunker.eval file <name>            # structural eval — single file + flagged detail
    uv run python -m rag.stg_02_chunker.eval llm openai             # LLM eval — gpt-4o-mini
    uv run python -m rag.stg_02_chunker.eval llm claude             # LLM eval — claude-haiku-4-5-20251001
    uv run python -m rag.stg_02_chunker.eval llm openai <n>         # LLM eval — sample n chunks (default 10)
    uv run python -m rag.stg_02_chunker.eval llm claude <n>
"""

import json
import sys
from pathlib import Path

from models.llm.config import LLMConfig, create_llm

from ..config import ChunkerConfig
from .metrics import MetricResult, quality_score, run_all
from .llm_metrics import run_llm

W = 60

_COLORS = [
    (95, "\033[38;2;88;198;138m"),  # #58C68A — Excellent
    (85, "\033[32m"),               # green   — Good
    (70, "\033[33m"),               # yellow  — Fair
    (50, "\033[31m"),               # red     — Poor
    (0,  "\033[91m"),               # bright red — Critical
]
_RESET = "\033[0m"


def _color(score: float, text: str) -> str:
    code = next(c for threshold, c in _COLORS if score >= threshold)
    return f"{code}{text}{_RESET}"


def _print_report(results: list[MetricResult], title: str, n_files: int, n_chunks: int) -> None:
    print("\n" + "═" * W)
    print(f"  {title}")
    print(f"  {n_files} file(s) · {n_chunks} chunks")
    print("═" * W)

    for r in results:
        detail = f"  {r.detail}" if r.detail else ""
        weight = f"  (w={r.weight:.2f})" if r.weight else ""
        line   = f"  {r.name:<26} {r.value:<12} {r.icon}{detail}{weight}"
        print(line)

    score, grade = quality_score(results)
    graded = [r for r in results if r.status != "info"]
    passed = sum(1 for r in graded if r.status == "pass")
    warned = sum(1 for r in graded if r.status == "warn")
    failed = sum(1 for r in graded if r.status == "fail")

    print("─" * W)
    print(f"  {'Quality score':<26} {_color(score, f'{score} / 100     {grade}')}")
    print(f"  {'Result':<26} {passed} pass · {warned} warn · {failed} fail")
    print("═" * W + "\n")


def _print_llm_details(results: list[MetricResult]) -> None:
    for r in results:
        if not r.flagged:
            continue
        print(f"\n── {r.name} — per chunk ──")
        for item in r.flagged:
            score    = item.get("score", "?")
            strength = item.get("strength", "")
            weakness = item.get("weakness", "")
            chunk_id = item.get("chunk_id", "?")
            color    = _color(score, f"{score:.0f}/100")
            print(f"\n  [{chunk_id}]  {color}")
            if strength:
                print(f"  + {strength}")
            if weakness:
                print(f"  - {weakness}")
        print()


def _print_flagged(results: list[MetricResult]) -> None:
    for r in results:
        if not r.flagged:
            continue
        print(f"\n── {r.name} ({len(r.flagged)} flagged) ──")
        for c in r.flagged[:5]:
            cid  = c.get("metadata", {}).get("chunk_id", "?")
            text = c["text"][:120].replace("\n", " ")
            print(f"  [{cid}] {text}…")
        if len(r.flagged) > 5:
            print(f"  … and {len(r.flagged) - 5} more")


def _load(path: Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)


cfg  = ChunkerConfig()
mode = sys.argv[1] if len(sys.argv) > 1 else "all"

if mode == "all":
    chunks_dir = Path(cfg.output_dir)
    files = sorted(chunks_dir.glob("*.json"))
    if not files:
        print(f"No chunk files found in {cfg.output_dir}")
        sys.exit(1)

    all_chunks: list[dict] = []
    for f in files:
        all_chunks.extend(_load(f))

    results = run_all(all_chunks, cfg.min_chunk_length, cfg.chunk_size)
    _print_report(results, "CHUNKER EVAL", len(files), len(all_chunks))

elif mode == "file":
    if len(sys.argv) < 3:
        print("Usage: uv run python -m rag.stg_02_chunker.eval file <path>")
        sys.exit(1)

    path   = Path(sys.argv[2])
    chunks = _load(path)
    results = run_all(chunks, cfg.min_chunk_length, cfg.chunk_size)
    _print_report(results, f"CHUNKER EVAL — {path.name}", 1, len(chunks))
    _print_flagged(results)

elif mode == "llm":
    if len(sys.argv) < 3 or sys.argv[2] not in ("openai", "claude"):
        print("Usage: uv run python -m rag.stg_02_chunker.eval llm openai|claude [n]")
        sys.exit(1)

    provider = sys.argv[2]
    sample_n = int(sys.argv[3]) if len(sys.argv) > 3 else 20

    chunks_dir = Path(cfg.output_dir)
    files = sorted(chunks_dir.glob("*.json"))
    if not files:
        print(f"No chunk files found in {cfg.output_dir}")
        sys.exit(1)

    all_chunks: list[dict] = []
    for f in files:
        all_chunks.extend(_load(f))

    if provider == "openai":
        llm = create_llm(LLMConfig(provider="openai", model="gpt-4o-mini"))
    else:
        llm = create_llm(LLMConfig(provider="anthropic", model="claude-haiku-4-5-20251001"))

    print(f"\nRunning LLM eval ({provider}) on {sample_n} sampled chunks ({len(all_chunks)} total)…")
    llm_results = run_llm(all_chunks, llm=llm, sample_n=sample_n)
    _print_report(llm_results, f"CHUNKER EVAL — LLM ({provider})", len(files), len(all_chunks))
    _print_llm_details(llm_results)

else:
    print(f"Unknown mode '{mode}'. Use: all | file | llm")
    sys.exit(1)
