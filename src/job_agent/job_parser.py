from __future__ import annotations

import re
from pathlib import Path

from .models import JobAnalysis


KNOWN_KEYWORDS = [
    "python",
    "sql",
    "r",
    "c++",
    "java",
    "excel",
    "pytorch",
    "transformers",
    "scikit-learn",
    "machine learning",
    "deep learning",
    "nlp",
    "llm",
    "large language model",
    "generative ai",
    "agent",
    "chatbot",
    "prompt engineering",
    "automation",
    "rpa",
    "workflow",
    "data analysis",
    "data preparation",
    "evaluation",
    "experiment design",
    "causal inference",
    "bayesian",
    "psychometrics",
    "item response theory",
    "vae",
    "documentation",
    "stakeholder",
    "international",
    "english",
    "german",
]


def parse_job_file(path: str | Path, company: str = "", title: str = "") -> JobAnalysis:
    job_path = Path(path)
    text = job_path.read_text(encoding="utf-8")
    inferred_title, inferred_company = _infer_header(text)
    return analyze_job_text(
        text,
        company=company or inferred_company or "Unknown company",
        title=title or inferred_title or job_path.stem.replace("_", " ").title(),
    )


def analyze_job_text(text: str, company: str, title: str) -> JobAnalysis:
    lines = [line.strip(" -•\t") for line in text.splitlines() if line.strip()]
    requirements = [
        line for line in lines if _looks_like_requirement(line)
    ][:12]
    responsibilities = [
        line for line in lines if _looks_like_responsibility(line)
    ][:12]
    lower = text.lower()
    keywords = [kw for kw in KNOWN_KEYWORDS if re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", lower)]
    return JobAnalysis(
        title=title,
        company=company,
        keywords=keywords,
        responsibilities=responsibilities,
        requirements=requirements,
        raw_text=text,
    )


def _looks_like_requirement(line: str) -> bool:
    lower = line.lower()
    markers = ["required", "requirement", "must", "qualification", "experience with", "proficiency", "knowledge of", "degree"]
    return any(marker in lower for marker in markers) or lower.startswith(("you have", "you bring", "skills"))


def _looks_like_responsibility(line: str) -> bool:
    lower = line.lower()
    markers = ["responsib", "build", "develop", "design", "support", "work with", "collaborate", "analyze", "automate", "implement"]
    return any(marker in lower for marker in markers)


def _infer_header(text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "", ""
    first = lines[0]
    if " at " in first.lower():
        title, company = re.split(r"\s+at\s+", first, maxsplit=1, flags=re.IGNORECASE)
        return title.strip(), company.strip()
    return first[:80], ""
