from __future__ import annotations

from .models import CandidateProfile, JobAnalysis, MatchResult


ROLE_KEYWORDS = {
    "ai_automation": ["llm", "large language model", "generative ai", "agent", "chatbot", "automation", "rpa", "workflow", "prompt engineering"],
    "ml_data": ["machine learning", "deep learning", "pytorch", "scikit-learn", "data analysis", "evaluation", "experiment design"],
    "nlp": ["nlp", "transformers", "information extraction", "entity", "relation extraction"],
    "research": ["causal inference", "bayesian", "psychometrics", "item response theory", "vae", "reproducible"],
    "business": ["documentation", "stakeholder", "international", "excel", "process"],
}


def match_profile_to_job(profile: CandidateProfile, job: JobAnalysis) -> MatchResult:
    evidence = profile.all_keywords
    normalized_evidence = set(evidence)
    job_keywords = _expanded_job_keywords(job)
    matched = []
    gaps = []

    for keyword in job_keywords:
        key = keyword.lower()
        if key in normalized_evidence:
            matched.append((keyword, evidence[key]))
        else:
            gaps.append(keyword)

    coverage = len(matched) / max(len(job_keywords), 1)
    role_bonus = _role_alignment_bonus(profile, job_keywords)
    score = min(98, round((coverage * 78) + role_bonus))
    decision = _decision(score, gaps)
    return MatchResult(score=score, decision=decision, matched=matched, gaps=gaps[:10], job=job)


def _expanded_job_keywords(job: JobAnalysis) -> list[str]:
    found = set(job.keywords)
    lower = job.raw_text.lower()
    for terms in ROLE_KEYWORDS.values():
        for term in terms:
            if term in lower:
                found.add(term)
    return sorted(found)


def _role_alignment_bonus(profile: CandidateProfile, job_keywords: list[str]) -> int:
    text = " ".join(profile.target_roles).lower()
    bonus = 0
    if any(term in job_keywords for term in ROLE_KEYWORDS["ai_automation"]) and ("ai" in text or "agent" in text or "automation" in text):
        bonus += 10
    if any(term in job_keywords for term in ROLE_KEYWORDS["ml_data"]) and ("machine learning" in text or "data" in text):
        bonus += 7
    if any(term in job_keywords for term in ROLE_KEYWORDS["research"]) and ("research" in text or "quantitative" in text):
        bonus += 5
    return bonus


def _decision(score: int, gaps: list[str]) -> str:
    if score >= 78:
        return "Strong apply: tailor the resume and apply."
    if score >= 60:
        return "Selective apply: apply if the company/role is attractive, and address the gaps explicitly."
    if score >= 42:
        return "Stretch role: useful for learning or networking, but customize carefully."
    return "Low fit: keep for market research unless there is a strong personal reason."
