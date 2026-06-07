from __future__ import annotations

import argparse
from pathlib import Path

from .generator import build_report, write_report
from .job_parser import parse_job_file
from .matcher import match_profile_to_job
from .memory import update_memory
from .profile import load_profile
from .tracker import add_application, list_applications
from .workflow import WORKFLOW_ENGINES, run_workflow


DEFAULT_PROFILE = Path("profiles/sample_candidate.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job-agent", description="Local-first job search agent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze = subparsers.add_parser("analyze", help="Analyze a job description and generate a match report")
    analyze.add_argument("--job", required=True, help="Path to a .txt or .md job description")
    analyze.add_argument("--profile", default=str(DEFAULT_PROFILE), help="Path to candidate profile JSON")
    analyze.add_argument("--company", default="", help="Override company name")
    analyze.add_argument("--title", default="", help="Override role title")
    analyze.add_argument("--out", default="", help="Write Markdown report to this path")
    analyze.add_argument("--memory", default="", help="Optional ignored local JSON memory file to update")

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

    workflow = subparsers.add_parser("workflow", help="Run a human-in-the-loop application workflow")
    workflow_sub = workflow.add_subparsers(dest="workflow_command", required=True)
    workflow_run = workflow_sub.add_parser("run", help="Analyze a role, gate red lines, and optionally produce a CV plan")
    workflow_run.add_argument("--job", required=True, help="Path to a .txt or .md job description")
    workflow_run.add_argument("--profile", default=str(DEFAULT_PROFILE), help="Path to candidate profile JSON")
    workflow_run.add_argument("--company", default="", help="Override company name")
    workflow_run.add_argument("--title", default="", help="Override role title")
    workflow_run.add_argument("--out-dir", default="", help="Directory for workflow artifacts")
    workflow_run.add_argument("--memory", default="", help="Optional ignored local JSON memory file to update")
    workflow_run.add_argument(
        "--engine",
        choices=sorted(WORKFLOW_ENGINES),
        default="classic",
        help="Workflow orchestrator. Use langgraph only after installing the optional extra.",
    )
    workflow_run.add_argument("--yes", action="store_true", help="Approve non-blocking workflow prompts")
    workflow_run.add_argument(
        "--llm-provider",
        choices=["none", "mock", "openai-compatible"],
        default="none",
        help="Optional LLM drafting provider. Default: none",
    )
    workflow_run.add_argument("--llm-model", default="", help="Model name for the optional LLM provider")
    workflow_run.add_argument(
        "--llm-base-url",
        default="",
        help="Base URL for OpenAI-compatible providers, e.g. http://localhost:11434/v1",
    )
    workflow_run.add_argument(
        "--llm-api-key-env",
        default="OPENAI_API_KEY",
        help="Environment variable containing an API key when the provider needs one",
    )

    args = parser.parse_args(argv)
    if args.command == "analyze":
        return _cmd_analyze(args)
    if args.command == "track":
        return _cmd_track(args)
    if args.command == "workflow":
        return _cmd_workflow(args)
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
    if args.memory:
        memory_path = update_memory(args.memory, result)
        print(f"Updated memory: {memory_path}")
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


def _cmd_workflow(args: argparse.Namespace) -> int:
    if args.workflow_command == "run":
        run = run_workflow(
            job_path=args.job,
            profile_path=args.profile,
            out_dir=args.out_dir or None,
            memory_path=args.memory or None,
            company=args.company,
            title=args.title,
            auto_approve=args.yes,
            llm_provider=args.llm_provider,
            llm_model=args.llm_model,
            llm_base_url=args.llm_base_url,
            llm_api_key_env=args.llm_api_key_env,
            engine=args.engine,
        )
        print(f"Workflow status: {run.status}")
        print(f"Wrote report: {run.artifacts.report}")
        print(f"Wrote decision: {run.artifacts.decision}")
        print(f"Wrote next actions: {run.artifacts.next_actions}")
        if run.artifacts.cv_plan:
            print(f"Wrote CV plan: {run.artifacts.cv_plan}")
        if run.artifacts.llm_cv_plan:
            print(f"Wrote optional LLM CV plan: {run.artifacts.llm_cv_plan}")
        if run.artifacts.llm_verification:
            print(f"Wrote LLM verification: {run.artifacts.llm_verification}")
        if run.artifacts.memory:
            print(f"Updated memory: {run.artifacts.memory}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
