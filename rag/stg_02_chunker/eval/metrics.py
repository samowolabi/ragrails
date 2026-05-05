"""
Structural quality metrics for chunker output.

All metrics are deterministic — no LLM calls needed.
Each metric carries a numeric score (0–100) and a weight used to compute
the overall quality score as a weighted average.

Weights (must sum to 1.0):
  embed_text_coverage   0.20  — missing embed_text directly hurts retrieval
  code_block_integrity  0.20  — split code blocks corrupt LLM context
  link_integrity        0.15  — broken links corrupt context
  size_compliance       0.15  — oversized chunks degrade embedding quality
  duplicate_rate        0.15  — duplicates inflate retrieval scores
  nav_noise             0.10  — noisy but not catastrophic
  heading_coverage      0.05  — helpful context, rarely missing
"""

import re
import statistics
from dataclasses import dataclass, field

from ..filters import is_link_heavy


STATUS_ICON = {"pass": "✓", "warn": "⚠", "fail": "✗", "info": "─"}

GRADE = [
    (95, "Excellent"),
    (85, "Good"),
    (70, "Fair"),
    (50, "Poor"),
    (0,  "Critical"),
]

_OPEN_LINK = re.compile(r"\[[^\]]*$")


@dataclass
class MetricResult:
    name: str
    value: str
    status: str                         # "pass" | "warn" | "fail" | "info"
    detail: str = ""
    flagged: list[dict] = field(default_factory=list, repr=False)
    score: float | None = None          # 0–100; None for info-only metrics
    weight: float = 0.0                 # contribution to overall quality score

    @property
    def icon(self) -> str:
        return STATUS_ICON.get(self.status, "─")


def quality_score(results: list[MetricResult]) -> tuple[float, str]:
    """Compute weighted average quality score and grade label.

    Example:
        score, grade = quality_score(results)
        # → (97.4, "Excellent")
    """
    scored = [r for r in results if r.score is not None]
    if not scored:
        return 0.0, "Critical"
    total_weight = sum(r.weight for r in scored)
    weighted_sum = sum(r.score * r.weight for r in scored)
    score = round(weighted_sum / total_weight, 1) if total_weight else 0.0
    grade = next(label for threshold, label in GRADE if score >= threshold)
    return score, grade


def _pct(n: int, total: int) -> float:
    return round(100 * n / total, 1) if total else 0.0


def size_stats(chunks: list[dict]) -> list[MetricResult]:
    """Chunk text length statistics — informational, no score.

    Example:
        size_stats([{"text": "hello world", ...}])
        # → [MetricResult("Size mean/median", "11 / 11 chars", "info"), ...]
    """
    lengths = [len(c["text"]) for c in chunks]
    if not lengths:
        return []
    mean   = statistics.mean(lengths)
    median = statistics.median(lengths)
    return [
        MetricResult("Size mean/median", f"{mean:.0f} / {median:.0f} chars", "info"),
        MetricResult("Size min/max",     f"{min(lengths)} / {max(lengths)} chars", "info"),
    ]


def size_compliance(chunks: list[dict], min_len: int = 50, max_len: int = 2000) -> MetricResult:
    """% of chunks within [min_len, max_len]. Score = that percentage.

    Example:
        size_compliance(chunks, min_len=50, max_len=2000)
        # → MetricResult("Size compliance", "94.2%", "pass", score=94.2, weight=0.15)
    """
    out   = [c for c in chunks if not (min_len <= len(c["text"]) <= max_len)]
    pct   = _pct(len(chunks) - len(out), len(chunks))
    status = "pass" if pct >= 90 else ("warn" if pct >= 75 else "fail")
    return MetricResult(
        "Size compliance", f"{pct}%", status,
        f"{len(out)} out of [{min_len}, {max_len}] range" if out else "",
        out, score=pct, weight=0.15,
    )


def nav_noise(chunks: list[dict]) -> MetricResult:
    """% of chunks that are link-heavy nav content. Score = 100 - noise_pct.

    Example:
        nav_noise(chunks)
        # → MetricResult("Nav noise", "3.1%", "pass", score=96.9, weight=0.10)
    """
    noisy  = [c for c in chunks if is_link_heavy(c["text"])]
    pct    = _pct(len(noisy), len(chunks))
    status = "pass" if pct <= 5 else ("warn" if pct <= 15 else "fail")
    return MetricResult(
        "Nav noise", f"{pct}%", status,
        f"{len(noisy)} link-heavy chunks" if noisy else "",
        noisy, score=round(100 - pct, 1), weight=0.10,
    )


def code_block_integrity(chunks: list[dict]) -> MetricResult:
    """% of chunks with no unclosed ``` fences. Score = that percentage.

    Example:
        code_block_integrity(chunks)
        # → MetricResult("Code block integrity", "100.0%", "pass", score=100.0, weight=0.20)
    """
    broken = [c for c in chunks if c["text"].count("```") % 2 != 0]
    pct    = _pct(len(chunks) - len(broken), len(chunks))
    status = "pass" if not broken else ("warn" if len(broken) / len(chunks) <= 0.02 else "fail")
    return MetricResult(
        "Code block integrity", f"{pct}%", status,
        f"{len(broken)} unclosed fences" if broken else "",
        broken, score=pct, weight=0.20,
    )


def link_integrity(chunks: list[dict]) -> MetricResult:
    """% of chunks with no broken markdown links. Score = that percentage.

    Example:
        link_integrity(chunks)
        # → MetricResult("Link integrity", "100.0%", "pass", score=100.0, weight=0.15)
    """
    broken = [c for c in chunks if _OPEN_LINK.search(c["text"])]
    pct    = _pct(len(chunks) - len(broken), len(chunks))
    status = "pass" if not broken else ("warn" if len(broken) / len(chunks) <= 0.02 else "fail")
    return MetricResult(
        "Link integrity", f"{pct}%", status,
        f"{len(broken)} open links" if broken else "",
        broken, score=pct, weight=0.15,
    )


def heading_coverage(chunks: list[dict]) -> MetricResult:
    """% of chunks with at least one heading in metadata. Score = that percentage.

    Example:
        heading_coverage(chunks)
        # → MetricResult("Heading coverage", "87.3%", "pass", score=87.3, weight=0.05)
    """
    with_heading = [c for c in chunks if c.get("metadata", {}).get("heading")]
    pct    = _pct(len(with_heading), len(chunks))
    status = "pass" if pct >= 60 else ("warn" if pct >= 30 else "fail")
    return MetricResult(
        "Heading coverage", f"{pct}%", status, "",
        [], score=pct, weight=0.05,
    )


def embed_text_coverage(chunks: list[dict]) -> MetricResult:
    """% of chunks with a non-empty embed_text field. Score = that percentage.

    Example:
        embed_text_coverage(chunks)
        # → MetricResult("Embed text coverage", "100.0%", "pass", score=100.0, weight=0.20)
    """
    missing = [c for c in chunks if not c.get("embed_text", "").strip()]
    pct     = _pct(len(chunks) - len(missing), len(chunks))
    status  = "pass" if pct >= 95 else ("warn" if pct >= 80 else "fail")
    return MetricResult(
        "Embed text coverage", f"{pct}%", status,
        f"{len(missing)} missing embed_text" if missing else "",
        missing, score=pct, weight=0.20,
    )


def duplicate_rate(chunks: list[dict]) -> MetricResult:
    """% of chunks with identical text to another. Score = 100 - duplicate_pct.

    Example:
        duplicate_rate(chunks)
        # → MetricResult("Duplicate rate", "0.0%", "pass", score=100.0, weight=0.15)
    """
    seen:  set[str] = set()
    dupes: list[dict] = []
    for c in chunks:
        t = c["text"]
        if t in seen:
            dupes.append(c)
        seen.add(t)
    pct    = _pct(len(dupes), len(chunks))
    status = "pass" if not dupes else ("warn" if pct <= 5 else "fail")
    return MetricResult(
        "Duplicate rate", f"{pct}%", status,
        f"{len(dupes)} duplicates" if dupes else "",
        dupes, score=round(100 - pct, 1), weight=0.15,
    )


def run_all(chunks: list[dict], min_len: int = 50, max_len: int = 2000) -> list[MetricResult]:
    """Run every metric on a chunk list and return results in display order.

    Example:
        results = run_all(chunks)
        score, grade = quality_score(results)
        # → (97.4, "Excellent")
    """
    return [
        *size_stats(chunks),
        size_compliance(chunks, min_len, max_len),
        nav_noise(chunks),
        code_block_integrity(chunks),
        link_integrity(chunks),
        heading_coverage(chunks),
        embed_text_coverage(chunks),
        duplicate_rate(chunks),
    ]
