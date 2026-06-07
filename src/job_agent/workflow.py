from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from .generator import build_report, write_report
from .job_parser import parse_job_file
from .matcher import match_profile_to_job
from .memory import update_memory
from .models import CandidateProfile, JobAnalysis, MatchResult
from .profile import load_profile


InputFn = Callable[[str], str]


@dataclass(frozen=True)
class WorkflowArtifacts:
    out_dir: Path
    report: Path
    decision: Path
    next_actions: Path
    cv_plan: Path | None = None
    memory: Path | None = None


@dataclass(frozen=True)
class WorkflowRun:
    status: str
    result: MatchResult
    artifacts: WorkflowArtifacts


class IntakeAgent:
    name = "intake"

    def load(self, job_path: str | Path, profile_path: str | Path, company: str = "", title: str = "") -> tuple[CandidateProfile, JobAnalysis]:
        profile = load_profile(profile_path)
        job = parse_job_file(job_path, company=company, title=title)
        return profile, job


class DecisionGateAgent:
    name = "decision_gate"

    def evaluate(self, profile: CandidateProfile, job: JobAnalysis) -> MatchResult:
        return match_profile_to_job(profile, job)

    def status(self, result: MatchResult) -> str:
        if any(signal.severity == "block" for signal in result.negative_signals):
            return "red_line_block"
        if result.negative_signals or result.market_risks:
            return "needs_verification"
        if result.score >= 78:
            return "ready_for_cv_plan"
        if result.score >= 60:
            return "selective_cv_plan"
        return "low_fit"


class ReportAgent:
    name = "report"

    def write(self, profile: CandidateProfile, result: MatchResult, out_dir: Path) -> tuple[Path, Path]:
        report_path = write_report(build_report(profile, result), out_dir / "report.md")
        decision_path = out_dir / "decision.json"
        decision_path.write_text(json.dumps(_decision_payload(result), indent=2, ensure_ascii=False), encoding="utf-8")
        return report_path, decision_path


class CVPlanAgent:
    name = "cv_plan"

    def build(self, result: MatchResult) -> str:
        lines = [
            f"# CV Targeting Plan: {result.job.title} at {result.job.company}",
            "",
            "## Gate",
            "",
            f"- Decision: {result.decision}",
            f"- Score: {result.score}/100",
            "",
            "## Claim-Evidence Table",
            "",
            "| Claim | Evidence | Label |",
            "|---|---|---|",
        ]
        for keyword, evidence in result.matched[:10]:
            sources = ", ".join(_unique_sources(evidence))
            lines.append(f"| Emphasize `{keyword}` | {sources} | safe |")
        for item in result.upskill_matches[:8]:
            lines.append(f"| Claim deep experience in `{item}` | No root evidence; prepare before interview | too strong / do not use |")
        for item in result.irrelevant_or_low_signal[:8]:
            lines.append(f"| Add `{item}` for keyword coverage | Unsupported or low-signal requirement | too strong / do not use |")
        if not result.matched:
            lines.append("| Strong role-specific claim | No direct evidence found | too strong / do not use |")

        lines.extend(
            [
                "",
                "## Safe Edits",
                "",
                "- Reorder existing evidence so the strongest matched items appear first.",
                "- Use concrete project wording from the profile; do not invent deployment, leadership, metrics, or tools.",
                "- Keep learnable gaps in interview prep unless private evidence confirms them.",
                "",
                "## Do Not Claim",
                "",
            ]
        )
        blocked = [signal.suggested_action for signal in result.negative_signals]
        blocked.extend(f"Do not claim unsupported strength in `{item}`." for item in result.irrelevant_or_low_signal[:8])
        blocked.extend(f"Do not present `{item}` as already mastered; keep it in upskill prep." for item in result.upskill_matches[:8])
        if not blocked:
            blocked.append("No specific do-not-claim item was detected by the local rules.")
        lines.extend(f"- {item}" for item in blocked)
        lines.extend(
            [
                "",
                "## Human Confirmation Needed",
                "",
                "- Confirm that every final CV bullet is evidence-backed.",
                "- Confirm that no private eligibility fact is copied into a public CV.",
                "- If this later becomes LaTeX output, compile and verify the PDF is exactly one page.",
            ]
        )
        return "\n".join(lines) + "\n"

    def write(self, result: MatchResult, out_dir: Path) -> Path:
        path = out_dir / "cv_plan.md"
        path.write_text(self.build(result), encoding="utf-8")
        return path


class NextActionsAgent:
    name = "next_actions"

    def write(self, status: str, result: MatchResult, out_dir: Path, cv_plan_path: Path | None) -> Path:
        path = out_dir / "next_actions.md"
        actions = _next_actions(status, result, cv_plan_path)
        path.write_text("\n".join(actions) + "\n", encoding="utf-8")
        return path


class MemoryAgent:
    name = "memory"

    def update(self, memory_path: str | Path, result: MatchResult) -> Path:
        return update_memory(memory_path, result)


def run_workflow(
    job_path: str | Path,
    profile_path: str | Path,
    out_dir: str | Path | None = None,
    memory_path: str | Path | None = None,
    company: str = "",
    title: str = "",
    auto_approve: bool = False,
    input_fn: InputFn = input,
) -> WorkflowRun:
    out = Path(out_dir) if out_dir else Path("outputs/private") / _slug(Path(job_path).stem)
    out.mkdir(parents=True, exist_ok=True)

    intake = IntakeAgent()
    gate = DecisionGateAgent()
    reporter = ReportAgent()
    cv_planner = CVPlanAgent()
    next_actions = NextActionsAgent()
    memory_agent = MemoryAgent()

    profile, job = intake.load(job_path, profile_path, company=company, title=title)
    result = gate.evaluate(profile, job)
    status = gate.status(result)
    report_path, decision_path = reporter.write(profile, result, out)

    cv_plan_path: Path | None = None
    if status == "red_line_block":
        pass
    elif status == "needs_verification":
        if _confirm("This role needs verification before CV tailoring. Generate a cautious CV plan anyway?", default=False, auto_approve=auto_approve, input_fn=input_fn):
            cv_plan_path = cv_planner.write(result, out)
    elif status in {"ready_for_cv_plan", "selective_cv_plan"}:
        if _confirm("Generate CV targeting plan?", default=True, auto_approve=auto_approve, input_fn=input_fn):
            cv_plan_path = cv_planner.write(result, out)

    memory_written: Path | None = None
    if memory_path and _confirm("Update local application memory?", default=True, auto_approve=auto_approve, input_fn=input_fn):
        memory_written = memory_agent.update(memory_path, result)

    next_actions_path = next_actions.write(status, result, out, cv_plan_path)
    artifacts = WorkflowArtifacts(
        out_dir=out,
        report=report_path,
        decision=decision_path,
        next_actions=next_actions_path,
        cv_plan=cv_plan_path,
        memory=memory_written,
    )
    return WorkflowRun(status=status, result=result, artifacts=artifacts)


def _confirm(prompt: str, default: bool, auto_approve: bool, input_fn: InputFn) -> bool:
    if auto_approve:
        return True
    suffix = "Y/n" if default else "y/N"
    try:
        answer = input_fn(f"{prompt} [{suffix}] ").strip().lower()
    except EOFError:
        return default
    if not answer:
        return default
    return answer in {"y", "yes"}


def _decision_payload(result: MatchResult) -> dict:
    return {
        "agent_status": DecisionGateAgent().status(result),
        "company": result.job.company,
        "role": result.job.title,
        "score": result.score,
        "decision": result.decision,
        "market_risks": result.market_risks,
        "negative_signals": [asdict(signal) for signal in result.negative_signals],
        "root_strengths": result.root_matches,
        "interview_upskill": result.upskill_matches,
        "do_not_claim": result.irrelevant_or_low_signal,
        "gaps": result.gaps,
    }


def _next_actions(status: str, result: MatchResult, cv_plan_path: Path | None) -> list[str]:
    lines = [
        f"# Next Actions: {result.job.title} at {result.job.company}",
        "",
        f"- Workflow status: **{status}**",
        f"- Decision: **{result.decision}**",
        "",
    ]
    if status == "red_line_block":
        lines.extend(
            [
                "## Stop Before Tailoring",
                "",
                "- Do not generate CV bullets or cover-letter text yet.",
                "- Resolve the red-line evidence privately first, or skip this role.",
            ]
        )
    elif status == "needs_verification":
        lines.extend(
            [
                "## Verify First",
                "",
                "- Confirm market filters or private eligibility facts before deep tailoring.",
                "- If confirmed, rerun the workflow or generate a cautious CV plan.",
            ]
        )
    elif cv_plan_path:
        lines.extend(
            [
                "## CV Plan Ready",
                "",
                f"- Review `{cv_plan_path}`.",
                "- Confirm each bullet is evidence-backed before editing the real CV.",
            ]
        )
    else:
        lines.extend(
            [
                "## No CV Plan Generated",
                "",
                "- Re-run with confirmation if you want a CV targeting plan.",
            ]
        )
    if result.memory_updates:
        lines.extend(["", "## Memory Notes", ""])
        lines.extend(f"- {item}" for item in result.memory_updates)
    return lines


def _unique_sources(evidence) -> list[str]:
    sources = []
    for item in evidence:
        if item.source not in sources:
            sources.append(item.source)
    return sources[:3]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return slug or "job_workflow"
