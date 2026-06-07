from __future__ import annotations

import json
from pathlib import Path

from .models import CandidateProfile


def load_profile(path: str | Path) -> CandidateProfile:
    profile_path = Path(path)
    data = json.loads(profile_path.read_text(encoding="utf-8"))
    return CandidateProfile.model_validate(data)
