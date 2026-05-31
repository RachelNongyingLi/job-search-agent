from __future__ import annotations

import argparse
from pathlib import Path

from .generator import build_report, write_report
from .job_parser import parse_job_file
from .matcher import match_profile_to_job
from .profile import load_profile
from .tracker import add_application, list_applications


DEFAULT_PROFILE = Path("profiles/nongying_public.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job-agent", description="Local-first job search agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze a job description and generate a match report")
    analyze.add_argument("--job", required=True, help="Path to a .txt or .md job description")
    analyze.add_argument("--profile", default=str(DEFAULT_PROFILE), help="Path to candidate profile JSON")
    analyze.add_argument("--company", default="", help="Override company name")
    analyze.add_argument("--title", default="", help="Override role title")
    analyze.add_argument("--out", default="", help="Write Markdown report to this path")

    track = subparsers.add_parser("track", help="Manage a CSV application tracker")
    track_sub = track.add_subparsers(dest="track_command", required=True)
    track_add = track_sub.add_parser("add", help="Add an application")
    track_add.add_argument("--csv", default="applications.csv")
    track_add.add_argument("--company", required=True)
    track_add.add_argument("--role", required=True)
    track_add.add_argument("--status", default="saved")
    track_add.add_argument("--link", default="")
    track_add.add_argument("--resume-version", default="")
    track_add.add_argument("--notes", default="")

    track_list = track_sub.add_parser("list", help="List applications")
    track_list.add_argument("--csv", default="applications.csv")

    args = parser.parse_args(argv)
    if args.command == "analyze":
        return _cmd_analyze(args)
    if args.command == "track":
        return _cmd_track(args)
    return 1


def _cmd_analyze(args: argparse.Namespace) -> int:
    profile = load_profile(args.profile)
    job = parse_job_file(args.job, company=args.company, title=args.title)
    result = match_profile_to_job(profile, job)
    report = build_report(profile, result)
    if args.out:
        path = write_report(report, args.out)
        print(f"Wrote report: {path}")
    else:
        print(report)
    return 0


def _cmd_track(args: argparse.Namespace) -> int:
    if args.track_command == "add":
        add_application(
            args.csv,
            company=args.company,
            role=args.role,
            status=args.status,
            link=args.link,
            resume_version=args.resume_version,
            notes=args.notes,
        )
        print(f"Added application: {args.company} - {args.role} [{args.status}]")
        return 0
    if args.track_command == "list":
        rows = list_applications(args.csv)
        if not rows:
            print("No applications tracked yet.")
            return 0
        widths = {key: max(len(key), *(len(row.get(key, "")) for row in rows)) for key in rows[0]}
        header = " | ".join(key.ljust(widths[key]) for key in rows[0])
        print(header)
        print("-+-".join("-" * widths[key] for key in rows[0]))
        for row in rows:
            print(" | ".join(row.get(key, "").ljust(widths[key]) for key in rows[0]))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
