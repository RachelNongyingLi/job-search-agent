from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

from .models import MatchResult


def update_memory(path: str | Path, result: MatchResult) -> Path:
    memory_path = Path(path)
    memory = _read_memory(memory_path)
    entry = {
        "date": date.today().isoformat(),
        "company": result.job.company,
        "role": result.job.title,
        "score": result.score,
        "decision": result.decision,
        "root_strengths": result.root_matches,
        "interview_upskill": result.upskill_matches,
        "market_risks": result.market_risks,
        "gaps": result.gaps,
    }
    memory.setdefault("applications", []).append(entry)
    memory["summary"] = _summarize(memory["applications"])
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    memory_path.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")
    return memory_path


def _read_memory(path: Path) -> dict:
    if not path.exists():
        return {"applications": [], "summary": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _summarize(applications: list[dict]) -> dict:
    root = Counter()
    upskill = Counter()
    risks = Counter()
    for app in applications:
        root.update(app.get("root_strengths", []))
        upskill.update(app.get("interview_upskill", []))
        risks.update(_risk_label(risk) for risk in app.get("market_risks", []))
    return {
        "top_root_strengths": root.most_common(10),
        "top_interview_upskill": upskill.most_common(10),
        "top_market_risks": risks.most_common(10),
        "application_count": len(applications),
    }


def _risk_label(risk: str) -> str:
    lower = risk.lower()
    if "german" in lower or "english" in lower or "language" in lower:
        return "language"
    if "authorization" in lower or "visa" in lower or "permit" in lower:
        return "work_authorization"
    if "location" in lower or "commute" in lower or "relocation" in lower or "onsite" in lower:
        return "location_or_commute"
    return "other_market_filter"
