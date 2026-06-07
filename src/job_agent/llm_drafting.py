from __future__ import annotations

import re

from .llm import LLMClient
from .models import MatchResult
from pydantic import BaseModel, ConfigDict


SYSTEM_PROMPT = """You are a cautious CV planning assistant.
You may draft wording advice only from the provided local analysis.
You must not invent eligibility, deployment, leadership, metrics, language fluency, work authorization, or proof documents.
If evidence is missing, label the item as interview prep, needs verification, or do not claim.
"""


class LLMVerification(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    warnings: list[str]
    checked_rules: list[str]


FORBIDDEN_POSITIVE_CLAIMS = {
    "deployed to production": "production deployment",
    "production ownership": "production ownership",
    "millions of users": "user-scale metric",
    "revenue impact": "business metric",
    "led a team": "leadership claim",
    "managed a team": "leadership claim",
    "german fluency": "language fluency",
    "native german": "language fluency",
    "work authorization": "work authorization",
    "visa sponsorship": "visa or authorization status",
    "mandatory internship proof": "eligibility proof",
    "certificate of mandatory internship": "eligibility proof",
}


def draft_cv_plan_with_llm(result: MatchResult, client: LLMClient) -> tuple[str, LLMVerification]:
    response = client.generate(
        prompt=build_cv_plan_prompt(result),
        system=SYSTEM_PROMPT,
        temperature=0.1,
        max_tokens=900,
    )
    text = _with_header(response.text, response.provider, response.model)
    verification = verify_llm_cv_plan(text, result)
    return text, verification


def build_cv_plan_prompt(result: MatchResult) -> str:
    return f"""Create a cautious CV targeting plan for this role.

Role: {result.job.title} at {result.job.company}
Decision: {result.decision}
Score: {result.score}/100

Matched evidence-backed keywords:
{_bullets(keyword for keyword, _ in result.matched[:12])}

Root strengths:
{_bullets(result.root_matches)}

Interview-upskill items:
{_bullets(result.upskill_matches)}

Low-signal or unsupported items:
{_bullets(result.irrelevant_or_low_signal)}

Negative signals:
{_bullets(signal.message for signal in result.negative_signals)}

Required output:
- Safe emphasis only.
- Evidence discipline.
- Do not claim list.
- One-page LaTeX CV reminder.
"""


def verify_llm_cv_plan(text: str, result: MatchResult) -> LLMVerification:
    warnings: list[str] = []
    checked_rules = [
        "no block-level red line",
        "no unsupported positive claim",
        "must mention evidence discipline",
        "must include do-not-claim guidance",
    ]
    lower = text.lower()

    if any(signal.severity == "block" for signal in result.negative_signals):
        warnings.append("Block-level red-line signal exists; LLM draft cannot be accepted.")

    for phrase, label in FORBIDDEN_POSITIVE_CLAIMS.items():
        if _has_unnegated_phrase(lower, phrase):
            warnings.append(f"Unsupported positive claim detected: {label}.")

    risky_terms = [*result.upskill_matches, *result.irrelevant_or_low_signal]
    for term in risky_terms:
        normalized = term.lower().strip()
        if normalized and _claims_deep_experience(lower, normalized):
            warnings.append(f"LLM draft upgrades an unverified or upskill item into deep experience: {term}.")

    if "evidence" not in lower:
        warnings.append("LLM draft must explicitly mention evidence discipline.")
    if "do not claim" not in lower and "do-not-claim" not in lower:
        warnings.append("LLM draft must include do-not-claim guidance.")

    return LLMVerification(passed=not warnings, warnings=warnings, checked_rules=checked_rules)


def _with_header(text: str, provider: str, model: str) -> str:
    return f"# Optional LLM CV Draft\n\nProvider: {provider}\nModel: {model}\n\n{text.strip()}\n"


def _bullets(items) -> str:
    values = [str(item) for item in items if str(item).strip()]
    if not values:
        return "- None detected by local analysis."
    return "\n".join(f"- {item}" for item in values)


def _has_unnegated_phrase(text: str, phrase: str) -> bool:
    start = 0
    while True:
        index = text.find(phrase, start)
        if index == -1:
            return False
        window = text[max(0, index - 60) : index]
        if not any(marker in window for marker in ["do not", "don't", "avoid", "never", "must not", "cannot", "without", "no "]):
            return True
        start = index + len(phrase)


def _claims_deep_experience(text: str, term: str) -> bool:
    escaped = re.escape(term)
    patterns = [
        rf"\b(deep|strong|proven|professional|production)\s+experience\s+(in|with)\s+{escaped}\b",
        rf"\b(expert|advanced|production-ready)\s+{escaped}\b",
        rf"\b{escaped}\s+(expert|ownership|leadership)\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)
