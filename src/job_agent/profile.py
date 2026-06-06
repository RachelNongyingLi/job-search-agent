from __future__ import annotations

import json
from pathlib import Path

from .models import CandidateProfile


def load_profile(path: str | Path) -> CandidateProfile:
    profile_path = Path(path)
    data = json.loads(profile_path.read_text(encoding="utf-8"))
    return CandidateProfile(
        name=data["name"],
        headline=data["headline"],
        target_roles=list(data.get("target_roles", [])),
        locations=list(data.get("locations", [])),
        education=list(data.get("education", [])),
        skills=dict(data.get("skills", {})),
        experiences=list(data.get("experiences", [])),
        projects=list(data.get("projects", [])),
        languages=list(data.get("languages", [])),
        market_facts=dict(data.get("market_facts", {})),
        ability_model=dict(data.get("ability_model", {})),
        notes=list(data.get("notes", [])),
    )
