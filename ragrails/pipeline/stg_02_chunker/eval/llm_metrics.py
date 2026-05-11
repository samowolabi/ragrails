"""
LLM-based quality metrics for chunker output.

Samples up to `sample_n` chunks. For each chunk the LLM returns a score,
a one-line strength, and a one-line weakness. The metric score is the mean
across all sampled chunks.

Weights (used for a separate LLM quality score):
  boundary_quality  0.40  — did the chunker split at a natural boundary?
  coherence         0.35  — is the chunk self-contained?
  retrievability    0.25  — can a search query plausibly surface this chunk?

informativeness is info-only — it reflects source content density, not chunking quality.
"""

import random

from ragrails.models.llm.base import LLMProvider
from ragrails.models.llm import usage_logger

from .metrics import MetricResult


_COHERENCE_PROMPT = """Rate how coherent this text chunk is on a scale of 0 to 100.
Judge only the chunk itself — does it form a complete, logical unit of content?
100 = clear and complete: the topic is introduced, explained, and concluded within this chunk.
0   = dangling fragment: starts mid-sentence, ends abruptly, or references content that isn't here.

Reply in exactly this format — nothing else:
SCORE: <number>
STRENGTH: <one sentence>
WEAKNESS: <one sentence>"""

_INFORMATIVENESS_PROMPT = """Rate how information-dense this text chunk is on a scale of 0 to 100.
100 = packed with substantive facts, parameters, code examples, or actionable technical detail.
0   = mostly boilerplate, navigation links, or filler with no actionable content.

Reply in exactly this format — nothing else:
SCORE: <number>
STRENGTH: <one sentence>
WEAKNESS: <one sentence>"""

_BOUNDARY_QUALITY_PROMPT = """Rate how cleanly this text chunk starts and ends on a scale of 0 to 100.
100 = starts at a natural boundary (heading or sentence start) and ends at a complete thought.
0   = starts mid-sentence or mid-thought, or cuts off before the idea is complete.

Reply in exactly this format — nothing else:
SCORE: <number>
STRENGTH: <one sentence>
WEAKNESS: <one sentence>"""

_RETRIEVABILITY_PROMPT = """Rate how retrievable this text chunk is on a scale of 0 to 100.
Imagine a user searches for the topic this chunk covers — would this chunk alone give them a useful answer?
100 = specific, complete, and independently actionable.
0   = too vague, too short, or an intro stub with no usable content.

Reply in exactly this format — nothing else:
SCORE: <number>
STRENGTH: <one sentence>
WEAKNESS: <one sentence>"""


def _parse(text: str) -> tuple[float, str, str]:
    """Parse SCORE / STRENGTH / WEAKNESS from the LLM reply.

    Example:
        _parse("SCORE: 82\\nSTRENGTH: Clear API steps.\\nWEAKNESS: Assumes prior auth knowledge.")
        # → (82.0, "Clear API steps.", "Assumes prior auth knowledge.")
    """
    score, strength, weakness = 50.0, "", ""
    for line in text.strip().splitlines():
        line = line.strip()
        if line.upper().startswith("SCORE:"):
            try:
                score = min(100.0, max(0.0, float(line.split(":", 1)[1].strip())))
            except ValueError:
                pass
        elif line.upper().startswith("STRENGTH:"):
            strength = line.split(":", 1)[1].strip()
        elif line.upper().startswith("WEAKNESS:"):
            weakness = line.split(":", 1)[1].strip()
    return score, strength, weakness


def _score_chunk(chunk: dict, llm: LLMProvider, system: str, action: str) -> dict:
    """Score one chunk and return a result dict with score, strength, weakness.

    Uses embed_text (title + heading + text) so the LLM sees the same context
    the embedding model sees — giving a fairer picture of retrieval quality.

    Example:
        result = _score_chunk(chunk, llm, _COHERENCE_PROMPT, "eval_coherence")
        # → {"chunk_id": "abc", "score": 82.0, "strength": "...", "weakness": "..."}
    """
    content = chunk.get("embed_text") or chunk["text"]
    response = llm.complete(system=system, user=content)
    usage_logger.log(response, action=action)
    score, strength, weakness = _parse(response.text)
    return {
        "chunk_id": chunk.get("metadata", {}).get("chunk_id", "?"),
        "score":    score,
        "strength": strength,
        "weakness": weakness,
        "text":     chunk["text"],
    }


def _sample(chunks: list[dict], n: int, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    return rng.sample(chunks, min(n, len(chunks)))


def coherence(
    chunks: list[dict],
    llm: LLMProvider,
    sample_n: int = 10,
) -> MetricResult:
    """Sample chunks and rate each for self-containment; score = mean rating.

    Example:
        result = coherence(chunks, llm=llm, sample_n=10)
        # → MetricResult("Coherence", "84.0 / 100", "pass", score=84.0, weight=0.60)
    """
    sample  = _sample(chunks, sample_n)
    results = [_score_chunk(c, llm, _COHERENCE_PROMPT, "eval_coherence") for c in sample]
    mean    = round(sum(r["score"] for r in results) / len(results), 1)
    status  = "pass" if mean >= 70 else ("warn" if mean >= 50 else "fail")
    return MetricResult(
        "Coherence",
        f"{mean:.1f} / 100",
        status,
        f"mean of {len(sample)} sampled chunks",
        flagged=results,
        score=mean,
        weight=0.35,
    )


def informativeness(
    chunks: list[dict],
    llm: LLMProvider,
    sample_n: int = 10,
) -> MetricResult:
    """Sample chunks and rate each for information density; score = mean rating.

    Example:
        result = informativeness(chunks, llm=llm, sample_n=10)
        # → MetricResult("Informativeness", "76.0 / 100", "pass", score=76.0, weight=0.40)
    """
    sample  = _sample(chunks, sample_n, seed=99)
    results = [_score_chunk(c, llm, _INFORMATIVENESS_PROMPT, "eval_informativeness") for c in sample]
    mean    = round(sum(r["score"] for r in results) / len(results), 1)
    status  = "pass" if mean >= 70 else ("warn" if mean >= 50 else "fail")
    return MetricResult(
        "Informativeness",
        f"{mean:.1f} / 100",
        "info",
        f"mean of {len(sample)} sampled chunks  (source quality)",
        flagged=results,
        score=None,
        weight=0.0,
    )


def boundary_quality(
    chunks: list[dict],
    llm: LLMProvider,
    sample_n: int = 10,
) -> MetricResult:
    """Sample chunks and rate each for clean start/end boundaries; score = mean rating.

    Example:
        result = boundary_quality(chunks, llm=llm, sample_n=10)
        # → MetricResult("Boundary quality", "91.0 / 100", "pass", score=91.0, weight=0.35)
    """
    sample  = _sample(chunks, sample_n, seed=7)
    results = [_score_chunk(c, llm, _BOUNDARY_QUALITY_PROMPT, "eval_boundary_quality") for c in sample]
    mean    = round(sum(r["score"] for r in results) / len(results), 1)
    status  = "pass" if mean >= 70 else ("warn" if mean >= 50 else "fail")
    return MetricResult(
        "Boundary quality",
        f"{mean:.1f} / 100",
        status,
        f"mean of {len(sample)} sampled chunks",
        flagged=results,
        score=mean,
        weight=0.40,
    )


def retrievability(
    chunks: list[dict],
    llm: LLMProvider,
    sample_n: int = 10,
) -> MetricResult:
    """Sample chunks and rate each for standalone search usefulness; score = mean rating.

    Example:
        result = retrievability(chunks, llm=llm, sample_n=10)
        # → MetricResult("Retrievability", "78.0 / 100", "pass", score=78.0, weight=0.20)
    """
    sample  = _sample(chunks, sample_n, seed=13)
    results = [_score_chunk(c, llm, _RETRIEVABILITY_PROMPT, "eval_retrievability") for c in sample]
    mean    = round(sum(r["score"] for r in results) / len(results), 1)
    status  = "pass" if mean >= 70 else ("warn" if mean >= 50 else "fail")
    return MetricResult(
        "Retrievability",
        f"{mean:.1f} / 100",
        status,
        f"mean of {len(sample)} sampled chunks",
        flagged=results,
        score=mean,
        weight=0.25,
    )


def run_llm(
    chunks: list[dict],
    llm: LLMProvider,
    sample_n: int = 10,
) -> list[MetricResult]:
    """Run all LLM metrics and return results; pass to quality_score() for a combined score.

    Example:
        results = run_llm(chunks, llm=llm, sample_n=10)
        score, grade = quality_score(results)
        # → (81.2, "Good")
    """
    return [
        boundary_quality(chunks, llm, sample_n),
        coherence(chunks, llm, sample_n),
        retrievability(chunks, llm, sample_n),
        informativeness(chunks, llm, sample_n),
    ]
