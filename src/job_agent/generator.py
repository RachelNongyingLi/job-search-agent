from __future__ import annotations

from pathlib import Path

from .models import CandidateProfile, MatchResult


def build_report(profile: CandidateProfile, result: MatchResult) -> str:
    job = result.job
    matched_lines = [
        f"- **{keyword}**: {', '.join(_summarize_sources(evidence))}"
        for keyword, evidence in result.matched[:14]
    ] or ["- No direct keyword matches found. Use this as a market-research role."]

    gaps = [f"- {gap}" for gap in result.gaps] or ["- No major keyword gaps detected by the local matcher."]
    resume_moves = _resume_moves(result)
    cover_letter = _cover_letter(profile, result)
    recruiter_message = _recruiter_message(profile, result)
    interview_prep = _interview_prep(result)

    return f"""# Job Match Report: {job.title} at {job.company}

## Fit Summary

- Fit score: **{result.score}/100**
- Decision: **{result.decision}**
- Candidate: {profile.name}
- Positioning: {profile.headline}

## Strong Evidence To Emphasize

{chr(10).join(matched_lines)}

## Gaps Or Risks To Handle

{chr(10).join(gaps)}

## Resume Targeting Plan

{chr(10).join(f"- {line}" for line in resume_moves)}

## Cover Letter Draft

{cover_letter}

## Recruiter Message

{recruiter_message}

## Interview Prep Prompts

{chr(10).join(f"- {line}" for line in interview_prep)}

## Application Checklist

- Save the job description and this report in the same application folder.
- Move the most relevant LLM/automation/NLP project into the top half of the resume when the role mentions AI assistants, agents, or workflow automation.
- Keep claims factual: use the project evidence above, avoid inventing production experience.
- Track the application status with `job-agent track add`.
"""


def write_report(markdown: str, out_path: str | Path) -> Path:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def _summarize_sources(evidence) -> list[str]:
    sources = []
    for item in evidence:
        if item.source not in sources:
            sources.append(item.source)
    return sources[:3]


def _resume_moves(result: MatchResult) -> list[str]:
    matched_keywords = {keyword.lower() for keyword, _ in result.matched}
    moves = []
    if {"llm", "agent", "automation", "generative ai", "chatbot"} & matched_keywords:
        moves.append("Lead with the CALE agentic AI project and describe prompt construction, inference, parsing, evaluation, and reproducible reporting.")
    if {"nlp", "transformers"} & matched_keywords:
        moves.append("Keep the joint entity and relation extraction project visible; frame it as structured knowledge extraction from unstructured text.")
    if {"data analysis", "evaluation", "experiment design", "machine learning"} & matched_keywords:
        moves.append("Quantify evaluation work where possible: baselines compared, metrics used, and reliability checks.")
    if {"documentation", "stakeholder", "international"} & matched_keywords:
        moves.append("Add one collaboration bullet showing clear communication with international technical and non-technical stakeholders.")
    if not moves:
        moves.append("Reorder skills so the job's top keywords appear in the first two lines of the Skills section.")
    moves.append("Use a filename that records company, role, and date, for example `Nongying_Li_AI_Automation_Analyst_2026-05.pdf`.")
    return moves


def _cover_letter(profile: CandidateProfile, result: MatchResult) -> str:
    job = result.job
    top = ", ".join(keyword for keyword, _ in result.matched[:5]) or "data science and machine learning"
    return (
        f"Dear Hiring Team,\n\n"
        f"I am a Quantitative Data Science master's student at the University of Tübingen, and I am excited to apply for the {job.title} role at {job.company}. "
        f"My background combines {top} with hands-on Python workflows for model evaluation, data preparation, and reproducible analysis.\n\n"
        f"In recent projects, I worked on agentic AI evaluation pipelines, NLP information extraction, causal inference workflows, and mask-aware VAE imputation for large-scale assessment data. "
        f"These experiences trained me to translate ambiguous analytical requirements into structured experiments, clear documentation, and practical automation outputs.\n\n"
        f"I would welcome the opportunity to bring this mix of AI, automation, and rigorous evaluation to {job.company}.\n\n"
        f"Best regards,\n{profile.name}"
    )


def _recruiter_message(profile: CandidateProfile, result: MatchResult) -> str:
    job = result.job
    return (
        f"Hi, I am {profile.name}, a Quantitative Data Science master's student at the University of Tübingen. "
        f"I saw the {job.title} role at {job.company} and noticed a strong overlap with my work in Python-based AI automation, LLM evaluation workflows, NLP information extraction, and reproducible data analysis. "
        f"I would be grateful if you could take a look at my application or let me know whether this profile fits the team."
    )


def _interview_prep(result: MatchResult) -> list[str]:
    prompts = [
        "Explain the CALE workflow as an end-to-end agentic AI pipeline: inputs, model calls, parsing, evaluation, and reporting.",
        "Prepare a concise story about turning an ambiguous research question into a reproducible Python workflow.",
        "Prepare a gap answer for any missing production/cloud experience: show how you would learn, test, and document safely.",
    ]
    if any(keyword in {"stakeholder", "international", "documentation"} for keyword, _ in result.matched):
        prompts.append("Prepare one communication story for explaining technical results to a mixed technical/non-technical audience.")
    return prompts
