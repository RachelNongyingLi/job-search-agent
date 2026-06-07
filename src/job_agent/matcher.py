from __future__ import annotations

from .models import CandidateProfile, JobAnalysis, MatchResult, NegativeSignal
from .negative_ability import detect_negative_signals


ROLE_KEYWORDS = {
    "ai_automation": ["llm", "large language model", "generative ai", "agent", "chatbot", "automation", "rpa", "workflow", "prompt engineering"],
    "ml_data": ["machine learning", "deep learning", "pytorch", "scikit-learn", "data analysis", "evaluation", "experiment design"],
    "nlp": ["nlp", "transformers", "information extraction", "entity", "relation extraction"],
    "research": ["causal inference", "bayesian", "psychometrics", "item response theory", "vae", "reproducible"],
    "business": ["documentation", "stakeholder", "international", "excel", "process"],
    "market": ["german", "english", "visa", "work authorization", "work permit", "relocation", "onsite", "on-site", "hybrid", "remote", "commute", "local candidate", "b1", "c1"],
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

    root_matches, upskill_matches, irrelevant_or_low_signal = _classify_abilities(profile, job_keywords)
    market_risks = _market_risks(profile, job)
    negative_signals = detect_negative_signals(profile, job, root_matches, upskill_matches)
    memory_updates = _memory_updates(job, root_matches, upskill_matches, market_risks, negative_signals)
    coverage = len(matched) / max(len(job_keywords), 1)
    role_bonus = _role_alignment_bonus(profile, job_keywords)
    market_penalty = min(18, len(market_risks) * 6)
    base_score = max(0, min(98, round((coverage * 78) + role_bonus - market_penalty)))
    score = min(base_score, _negative_score_cap(negative_signals))
    decision = _decision(score, gaps, market_risks, negative_signals)
    return MatchResult(
        score=score,
        decision=decision,
        matched=matched,
        gaps=gaps[:10],
        root_matches=root_matches,
        upskill_matches=upskill_matches,
        irrelevant_or_low_signal=irrelevant_or_low_signal,
        market_risks=market_risks,
        memory_updates=memory_updates,
        job=job,
        negative_signals=negative_signals,
    )


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


def _classify_abilities(profile: CandidateProfile, job_keywords: list[str]) -> tuple[list[str], list[str], list[str]]:
    ability = profile.ability_model or {}
    root = _lower_set(ability.get("root_strengths", []))
    upskill = _lower_set(ability.get("interview_upskill", []))
    irrelevant = _lower_set(ability.get("irrelevant_or_low_signal", []))
    root_matches = []
    upskill_matches = []
    irrelevant_or_low_signal = []

    for keyword in job_keywords:
        key = keyword.lower()
        if key in root:
            root_matches.append(keyword)
        elif _soft_contains(key, upskill):
            upskill_matches.append(keyword)
        elif _soft_contains(key, irrelevant):
            irrelevant_or_low_signal.append(keyword)

    if not upskill_matches:
        for gap in job_keywords:
            if gap in {"cloud", "deployment", "production", "dashboard", "rpa"}:
                upskill_matches.append(gap)
    return root_matches, upskill_matches, irrelevant_or_low_signal


def _market_risks(profile: CandidateProfile, job: JobAnalysis) -> list[str]:
    facts = profile.market_facts or {}
    raw = job.raw_text.lower()
    claimed_languages = _lower_set(facts.get("languages_claimed", []))
    not_claimed_languages = _lower_set(facts.get("languages_not_claimed", []))
    risks = []

    if "german" in raw and "german" in not_claimed_languages:
        risks.append("German is requested, but the public profile does not claim German proficiency.")
    if ("visa" in raw or "work authorization" in raw or "work permit" in raw) and "keep private" in str(facts.get("work_authorization", "")).lower():
        risks.append("Work authorization is a hard filter. Keep it private publicly, but verify locally before applying.")
    if any(term in raw for term in ["onsite", "on-site", "commute", "local candidate", "relocation"]):
        risks.append("Location, commute, or relocation may matter more than technical fit. Confirm locally before treating this as a strong application.")
    if "english" in raw and "english" not in claimed_languages:
        risks.append("English is requested, but the profile does not explicitly claim English.")
    return risks


def _memory_updates(
    job: JobAnalysis,
    root_matches: list[str],
    upskill_matches: list[str],
    market_risks: list[str],
    negative_signals: list[NegativeSignal],
) -> list[str]:
    updates = []
    if negative_signals:
        labels = ", ".join(signal.code for signal in negative_signals[:4])
        updates.append(f"Preserve negative evidence separately; do not let memory convert red lines into strengths: {labels}.")
    if root_matches:
        updates.append(f"Strengthen memory for this market cluster: {', '.join(root_matches[:6])}.")
    if upskill_matches:
        updates.append(f"Add short learning tasks before interview: {', '.join(upskill_matches[:5])}.")
    if market_risks:
        updates.append("Record market filters that affected this application: language, location, commute, or work authorization.")
    if not updates:
        updates.append("No new memory updates suggested by the rule-based matcher.")
    return updates


def _lower_set(values: list[str]) -> set[str]:
    return {str(value).lower() for value in values}


def _soft_contains(keyword: str, values: set[str]) -> bool:
    return any(keyword in value or value in keyword for value in values)


def _negative_score_cap(negative_signals: list[NegativeSignal]) -> int:
    if not negative_signals:
        return 98
    return min(signal.score_cap for signal in negative_signals)


def _decision(score: int, gaps: list[str], market_risks: list[str], negative_signals: list[NegativeSignal]) -> str:
    if any(signal.severity == "block" for signal in negative_signals):
        return "Red-line block: verify or skip before tailoring; do not turn missing evidence into resume claims."
    if negative_signals:
        return "Verify first: negative ability signals cap this match until local evidence is confirmed."
    if market_risks and score >= 78:
        return "Strong technical fit, but verify market hard filters before applying."
    if market_risks:
        return "Market-filter risk: verify language, location, commute, or work authorization before deep tailoring."
    if score >= 78:
        return "Strong apply: tailor the resume and apply."
    if score >= 60:
        return "Selective apply: apply if the company/role is attractive, and address the gaps explicitly."
    if score >= 42:
        return "Stretch role: useful for learning or networking, but customize carefully."
    return "Low fit: keep for market research unless there is a strong personal reason."
