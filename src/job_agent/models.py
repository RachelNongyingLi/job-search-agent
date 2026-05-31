from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Evidence:
    label: str
    source: str
    weight: int = 1


@dataclass
class CandidateProfile:
    name: str
    headline: str
    target_roles: list[str]
    locations: list[str]
    education: list[dict]
    skills: dict[str, list[str]]
    experiences: list[dict]
    projects: list[dict]
    languages: list[str]
    notes: list[str] = field(default_factory=list)

    @property
    def all_keywords(self) -> dict[str, list[Evidence]]:
        buckets: dict[str, list[Evidence]] = {}

        def add(term: str, source: str, weight: int = 1) -> None:
            key = term.lower().strip()
            if not key:
                return
            buckets.setdefault(key, []).append(Evidence(term, source, weight))

        for group, values in self.skills.items():
            for value in values:
                add(value, f"skill:{group}", 3)
                for alias in _aliases(value):
                    add(alias, f"skill:{group}", 2)

        for role in self.target_roles:
            add(role, "target role", 2)

        for item in [*self.experiences, *self.projects]:
            title = str(item.get("title", ""))
            add(title, "experience/project title", 2)
            for keyword in item.get("keywords", []):
                add(str(keyword), title or "experience/project", 3)
                for alias in _aliases(str(keyword)):
                    add(alias, title or "experience/project", 2)
            for bullet in item.get("bullets", []):
                for token in _important_phrases(str(bullet)):
                    add(token, title or "experience/project", 1)

        for edu in self.education:
            for field in ("degree", "institution", "focus"):
                add(str(edu.get(field, "")), "education", 1)

        for language in self.languages:
            add(language, "language", 2)
            for alias in _aliases(language):
                add(alias, "language", 2)

        return buckets


def _aliases(term: str) -> list[str]:
    lower = term.lower()
    aliases = {
        "stakeholder communication": ["stakeholder", "communication"],
        "international collaboration": ["international", "collaboration"],
        "as-is/to-be analysis": ["process", "process improvement"],
        "data preparation": ["data analysis"],
        "model evaluation": ["evaluation"],
        "python workflow": ["python", "workflow"],
        "automated evaluation": ["automation", "evaluation"],
        "english: professional working proficiency": ["english"],
        "mandarin chinese: native": ["mandarin", "chinese"],
        "large language model": ["llm"],
        "item response theory": ["irt"],
    }
    return aliases.get(lower, [])


@dataclass(frozen=True)
class JobAnalysis:
    title: str
    company: str
    keywords: list[str]
    responsibilities: list[str]
    requirements: list[str]
    raw_text: str


@dataclass(frozen=True)
class MatchResult:
    score: int
    decision: str
    matched: list[tuple[str, list[Evidence]]]
    gaps: list[str]
    job: JobAnalysis


def _important_phrases(text: str) -> list[str]:
    phrases = [
        "large language model",
        "llm",
        "agent",
        "automation",
        "workflow",
        "python",
        "pytorch",
        "transformer",
        "nlp",
        "causal inference",
        "rnn",
        "vae",
        "item response theory",
        "irt",
        "evaluation",
        "data preprocessing",
        "prompt",
        "reproducible",
        "documentation",
    ]
    lower = text.lower()
    return [phrase for phrase in phrases if phrase in lower]
