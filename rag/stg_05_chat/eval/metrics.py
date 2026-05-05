"""Metrics and helpers for end-to-end RAG evaluation.

The eval runner uses a small JSONL golden set. Each row describes one user
question plus the evidence and terms we expect a good RAG answer to use.

Example JSONL row:
    {"id":"auth","question":"How do I authenticate?","expected_sources":["api-basics"],"required_terms":["Bearer"]}
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from models.llm import usage_logger
from models.llm.base import LLMProvider
from models.vector_db.base import SearchResult


GRADE = [
    (90, "Excellent"),
    (80, "Good"),
    (70, "Fair"),
    (55, "Poor"),
    (0, "Critical"),
]

_CITATION_RE = re.compile(r"\[(C\d+|invalid:C\d+)\]")
_JUDGE_SYSTEM = """You are a strict evaluator for RAG answers.
Score only from the provided context and expected checks.
Return valid JSON only."""
_JUDGE_PROMPT = """Question:
{question}

Answer:
{answer}

Retrieved context:
{context}

Expected source hints:
{expected_sources}

Required terms:
{required_terms}

Score 0-100 for:
- faithfulness: answer claims are supported by retrieved context
- relevance: answer directly addresses the question
- completeness: answer includes the important details implied by required terms/source hints

Return exactly:
{{"faithfulness": <number>, "relevance": <number>, "completeness": <number>, "explanation": "<one sentence>"}}"""


@dataclass
class EvalCase:
    id: str
    question: str
    expected_sources: list[str] = field(default_factory=list)
    required_terms: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class JudgeScore:
    faithfulness: float = 0.0
    relevance: float = 0.0
    completeness: float = 0.0
    explanation: str = ""

    @property
    def score(self) -> float:
        return round((self.faithfulness * 0.45) + (self.relevance * 0.30) + (self.completeness * 0.25), 1)


@dataclass
class EvalResult:
    case: EvalCase
    rewritten_query: str
    ranked: list[SearchResult]
    used_sources: list[dict]
    answer: str = ""
    retrieval_hit: bool = False
    top1_hit: bool = False
    reciprocal_rank: float = 0.0
    required_terms_found: list[str] = field(default_factory=list)
    required_terms_missing: list[str] = field(default_factory=list)
    citations_valid: bool = True
    judge: JudgeScore | None = None
    error: str = ""

    @property
    def deterministic_score(self) -> float:
        retrieval = 100.0 if self.retrieval_hit else 0.0
        top1 = 100.0 if self.top1_hit else 0.0
        terms = _pct(len(self.required_terms_found), len(self.case.required_terms)) if self.case.required_terms else 100.0
        citations = 100.0 if self.citations_valid else 0.0
        return round(retrieval * 0.45 + top1 * 0.20 + terms * 0.25 + citations * 0.10, 1)

    @property
    def overall_score(self) -> float:
        if self.judge is None:
            return self.deterministic_score
        return round(self.deterministic_score * 0.55 + self.judge.score * 0.45, 1)


def load_cases(path: str) -> list[EvalCase]:
    """Load JSONL eval cases."""
    rows: list[EvalCase] = []
    for lineno, line in enumerate(Path(path).read_text().splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}:{lineno}: invalid JSON: {e}") from e
        rows.append(EvalCase(
            id=data.get("id") or f"case-{lineno}",
            question=data["question"],
            expected_sources=list(data.get("expected_sources", [])),
            required_terms=list(data.get("required_terms", [])),
            notes=data.get("notes", ""),
        ))
    return rows


def retrieval_metrics(case: EvalCase, ranked: list[SearchResult]) -> tuple[bool, bool, float]:
    """Return retrieval hit, top-1 hit, and reciprocal rank for expected sources."""
    if not case.expected_sources:
        return True, True, 1.0

    first_rank = None
    for idx, result in enumerate(ranked, start=1):
        if result_matches_expected(result, case.expected_sources):
            first_rank = idx
            break

    if first_rank is None:
        return False, False, 0.0
    return True, first_rank == 1, round(1 / first_rank, 3)


def result_matches_expected(result: SearchResult, expected_sources: list[str]) -> bool:
    """Match expected source hints against chunk id, title, heading, path, or text."""
    haystack = _result_haystack(result)
    return any(expected.lower() in haystack for expected in expected_sources)


def required_term_metrics(answer: str, terms: list[str]) -> tuple[list[str], list[str]]:
    """Return required terms found/missing in an answer."""
    text = answer.lower()
    found = [term for term in terms if term.lower() in text]
    missing = [term for term in terms if term.lower() not in text]
    return found, missing


def citations_are_valid(answer: str, sources: list[dict]) -> bool:
    """Check that generated inline citations map to current chunk sources."""
    valid = {source["id"] for source in sources}
    for match in _CITATION_RE.finditer(answer):
        citation = match.group(1)
        if citation.startswith("invalid:") or citation not in valid:
            return False
    return True


def judge_answer(case: EvalCase, answer: str, ranked: list[SearchResult], llm: LLMProvider) -> JudgeScore:
    """Use an LLM judge to score faithfulness/relevance/completeness."""
    prompt = _JUDGE_PROMPT.format(
        question=case.question,
        answer=answer,
        context=_context_for_judge(ranked),
        expected_sources=", ".join(case.expected_sources) or "none",
        required_terms=", ".join(case.required_terms) or "none",
    )
    response = llm.complete(system=_JUDGE_SYSTEM, user=prompt, temperature=0.0)
    usage_logger.log(response, action="eval_answer_judge")
    return _parse_judge(response.text)


def quality_score(results: list[EvalResult]) -> tuple[float, str]:
    """Return mean overall score and grade."""
    if not results:
        return 0.0, "Critical"
    score = round(sum(r.overall_score for r in results) / len(results), 1)
    grade = next(label for threshold, label in GRADE if score >= threshold)
    return score, grade


def _parse_judge(text: str) -> JudgeScore:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.S).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return JudgeScore(explanation=f"Could not parse judge response: {text[:160]}")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return JudgeScore(explanation=f"Could not parse judge response: {text[:160]}")

    return JudgeScore(
        faithfulness=_clamp(data.get("faithfulness", 0)),
        relevance=_clamp(data.get("relevance", 0)),
        completeness=_clamp(data.get("completeness", 0)),
        explanation=str(data.get("explanation", "")),
    )


def _context_for_judge(ranked: list[SearchResult], limit: int = 5) -> str:
    blocks = []
    for i, result in enumerate(ranked[:limit], start=1):
        heading = result.metadata.get("heading", {})
        heading_text = " > ".join(heading.values()) if isinstance(heading, dict) else str(heading or "")
        blocks.append(
            f"[C{i}] {result.metadata.get('title', '')} {heading_text}\n"
            f"{result.metadata.get('path', '')}\n"
            f"{result.text[:1500]}"
        )
    return "\n\n---\n\n".join(blocks)


def _result_haystack(result: SearchResult) -> str:
    meta = result.metadata
    heading = meta.get("heading", {})
    heading_text = " ".join(heading.values()) if isinstance(heading, dict) else str(heading or "")
    parts = [
        result.id,
        meta.get("id", ""),
        meta.get("chunk_id", ""),
        meta.get("title", ""),
        meta.get("path", ""),
        heading_text,
        result.text,
    ]
    return " ".join(str(part) for part in parts if part).lower()


def _pct(num: int, den: int) -> float:
    return round(100 * num / den, 1) if den else 0.0


def _clamp(value: object) -> float:
    try:
        return min(100.0, max(0.0, float(value)))
    except (TypeError, ValueError):
        return 0.0
