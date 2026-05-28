"""
Query rewrite eval metrics.

For each (original, rewritten) pair the LLM scores three properties:
  specificity        — did the rewrite add technical terminology, endpoints, or parameters?
  intent_preservation — does the rewrite still answer the same question?
  expansion_quality  — did it usefully add prerequisites or related operations?

Weights (must sum to 1.0):
  intent_preservation  0.45  — a rewrite that changes intent is worse than no rewrite
  specificity          0.35  — the primary value of rewriting for API docs
  expansion_quality    0.20  — useful but secondary
"""

from dataclasses import dataclass

from ragrails.models.llm.base import LLMProvider
from ragrails.models.llm import usage_logger


GRADE = [
    (90, "Excellent"),
    (75, "Good"),
    (60, "Fair"),
    (40, "Poor"),
    (0,  "Critical"),
]

_WEIGHTS = {
    "intent_preservation": 0.45,
    "specificity":         0.35,
    "expansion_quality":   0.20,
}

_SCORE_PROMPT = """You are evaluating a query rewrite for API documentation search.

Original query: {original}
Rewritten query: {rewritten}

Score the rewrite on three dimensions (0–100 each):

SPECIFICITY: Did the rewrite add technical detail — endpoint names, HTTP methods, parameters, or developer terminology?
  100 = rich technical expansion   0 = no technical detail added

INTENT: Does the rewrite still answer the same question the user asked?
  100 = identical intent   0 = completely different meaning

EXPANSION: Did the rewrite usefully add prerequisite steps or related operations needed to fully answer the question?
  100 = well-scoped expansion   0 = no useful expansion, or expanded in the wrong direction

Reply in exactly this format — nothing else:
SPECIFICITY: <number>
INTENT: <number>
EXPANSION: <number>"""

_QUESTION_PROMPT = """Given this documentation chunk, write one natural language question that a developer would ask whose answer is in this chunk.
The question should sound like something typed into a search box — conversational, not technical jargon.
Return only the question, no explanation."""


@dataclass
class RewriteResult:
    original:    str
    rewritten:   str
    specificity: float
    intent:      float
    expansion:   float
    score:       float   # weighted average


def _parse(text: str) -> tuple[float, float, float]:
    """Parse SPECIFICITY / INTENT / EXPANSION from the LLM reply.

    Example:
        _parse("SPECIFICITY: 85\\nINTENT: 95\\nEXPANSION: 70")
        # → (85.0, 95.0, 70.0)
    """
    specificity, intent, expansion = 50.0, 50.0, 50.0
    for line in text.strip().splitlines():
        line = line.strip()
        key, _, val = line.partition(":")
        try:
            v = min(100.0, max(0.0, float(val.strip())))
        except ValueError:
            continue
        if key.upper() == "SPECIFICITY":
            specificity = v
        elif key.upper() == "INTENT":
            intent = v
        elif key.upper() == "EXPANSION":
            expansion = v
    return specificity, intent, expansion


def generate_question(chunk: dict, llm: LLMProvider) -> str:
    """Ask the LLM to generate a natural language question answered by this chunk.

    Example:
        q = generate_question(chunk, llm)
        # → "How do I authenticate requests to the BudPay API?"
    """
    text = chunk.get("embed_text") or chunk["text"]
    response = llm.complete(system=_QUESTION_PROMPT, user=text)
    usage_logger.log(response, action="eval_question_gen")
    return response.text.strip()


def score_rewrite(original: str, rewritten: str, llm: LLMProvider) -> RewriteResult:
    """Score a single (original, rewritten) query pair on all three dimensions.

    Example:
        result = score_rewrite("how do I send money", "initiate POST /transfer...", llm)
        # → RewriteResult(specificity=88.0, intent=95.0, expansion=72.0, score=88.4)
    """
    prompt = _SCORE_PROMPT.format(original=original, rewritten=rewritten)
    response = llm.complete(system=prompt, user="")
    usage_logger.log(response, action="eval_rewrite_score")
    specificity, intent, expansion = _parse(response.text)
    score = round(
        specificity * _WEIGHTS["specificity"]
        + intent    * _WEIGHTS["intent_preservation"]
        + expansion * _WEIGHTS["expansion_quality"],
        1,
    )
    return RewriteResult(
        original=original,
        rewritten=rewritten,
        specificity=specificity,
        intent=intent,
        expansion=expansion,
        score=score,
    )


def quality_score(results: list[RewriteResult]) -> tuple[float, str]:
    """Compute mean score across all rewrite results and return grade label.

    Example:
        score, grade = quality_score(results)
        # → (83.5, "Good")
    """
    if not results:
        return 0.0, "Critical"
    mean = round(sum(r.score for r in results) / len(results), 1)
    grade = next(label for threshold, label in GRADE if mean >= threshold)
    return mean, grade
