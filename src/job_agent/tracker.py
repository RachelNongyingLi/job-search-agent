from __future__ import annotations

import csv
from datetime import date
from pathlib import Path


FIELDS = ["date", "company", "role", "status", "link", "resume_version", "notes"]


def add_application(path: str | Path, company: str, role: str, status: str, link: str = "", resume_version: str = "", notes: str = "") -> None:
    csv_path = Path(path)
    exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "date": date.today().isoformat(),
                "company": company,
                "role": role,
                "status": status,
                "link": link,
                "resume_version": resume_version,
                "notes": notes,
            }
        )


def list_applications(path: str | Path) -> list[dict[str, str]]:
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
