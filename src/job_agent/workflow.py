from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field

from .generator import build_report, write_report
from .job_parser import parse_job_file
from .llm import LLMClient, LLMProviderError, build_llm_client
from .llm_drafting import LLMVerification, draft_cv_plan_with_llm
from .matcher import match_profile_to_job
from .memory import update_memory
from .models import CandidateProfile, JobAnalysis, MatchResult
from .profile import load_profile


InputFn = Callable[[str], str]
DEFAULT_WORKFLOW_ENGINE = "langgraph"
WORKFLOW_ENGINES = {"classic", "langgraph"}


class WorkflowEngineError(RuntimeError):
    """Raised when a requested workflow orchestrator cannot run."""


class WorkflowCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: str
    title: str
    message: str
    action: str
    risk_level: str = "human_required"
    requires: list[str] = Field(default_factory=list)
    state_summary: dict[str, Any] = Field(default_factory=dict)
    id: str | None = None


class WorkflowArtifacts(BaseModel):
    model_config = ConfigDict(frozen=True)

    out_dir: Path
    report: Path | None = None
    decision: Path | None = None
    next_actions: Path | None = None
    cv_plan: Path | None = None
    llm_cv_plan: Path | None = None
    llm_verification: Path | None = None
    memory: Path | None = None


class WorkflowRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: str
    result: MatchResult
    artifacts: WorkflowArtifacts
    pending_checkpoint: WorkflowCheckpoint | None = None
    thread_id: str | None = None


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

    def write(
        self,
        status: str,
        result: MatchResult,
        out_dir: Path,
        cv_plan_path: Path | None,
        llm_cv_plan_path: Path | None = None,
        llm_verification_path: Path | None = None,
    ) -> Path:
        path = out_dir / "next_actions.md"
        actions = _next_actions(status, result, cv_plan_path, llm_cv_plan_path, llm_verification_path)
        path.write_text("\n".join(actions) + "\n", encoding="utf-8")
        return path


class MemoryAgent:
    name = "memory"

    def update(self, memory_path: str | Path, result: MatchResult) -> Path:
        return update_memory(memory_path, result)


class LLMDraftAgent:
    name = "llm_draft"

    def write(self, result: MatchResult, out_dir: Path, client: LLMClient) -> tuple[Path | None, Path]:
        verification_path = out_dir / "llm_verification.json"
        try:
            text, verification = draft_cv_plan_with_llm(result, client)
        except (LLMProviderError, ValueError) as exc:
            payload = _llm_verification_payload(
                LLMVerification(
                    passed=False,
                    warnings=[str(exc)],
                    checked_rules=["provider returned usable response"],
                ),
                provider=getattr(client, "provider", "unknown"),
                model=getattr(client, "model", "unknown"),
            )
            verification_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
            return None, verification_path

        payload = _llm_verification_payload(verification, provider=client.provider, model=client.model)
        verification_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        if not verification.passed:
            return None, verification_path
        draft_path = out_dir / "cv_plan.llm.md"
        draft_path.write_text(text, encoding="utf-8")
        return draft_path, verification_path


def run_workflow(
    job_path: str | Path,
    profile_path: str | Path,
    out_dir: str | Path | None = None,
    memory_path: str | Path | None = None,
    company: str = "",
    title: str = "",
    auto_approve: bool = False,
    input_fn: InputFn = input,
    llm_provider: str = "none",
    llm_model: str = "",
    llm_base_url: str = "",
    llm_api_key_env: str = "OPENAI_API_KEY",
    llm_client: LLMClient | None = None,
    engine: str = DEFAULT_WORKFLOW_ENGINE,
    thread_id: str | None = None,
    checkpointer: Any = None,
    resume: Any = None,
) -> WorkflowRun:
    workflow_engine = _normalize_engine(engine)
    if workflow_engine == "langgraph":
        from .langgraph_workflow import run_langgraph_workflow

        return run_langgraph_workflow(
            job_path=job_path,
            profile_path=profile_path,
            out_dir=out_dir,
            memory_path=memory_path,
            company=company,
            title=title,
            auto_approve=auto_approve,
            input_fn=input_fn,
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            llm_api_key_env=llm_api_key_env,
            llm_client=llm_client,
            thread_id=thread_id,
            checkpointer=checkpointer,
            resume=resume,
        )
    return _run_classic_workflow(
        job_path=job_path,
        profile_path=profile_path,
        out_dir=out_dir,
        memory_path=memory_path,
        company=company,
        title=title,
        auto_approve=auto_approve,
        input_fn=input_fn,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        llm_api_key_env=llm_api_key_env,
        llm_client=llm_client,
    )


def _run_classic_workflow(
    job_path: str | Path,
    profile_path: str | Path,
    out_dir: str | Path | None = None,
    memory_path: str | Path | None = None,
    company: str = "",
    title: str = "",
    auto_approve: bool = False,
    input_fn: InputFn = input,
    llm_provider: str = "none",
    llm_model: str = "",
    llm_base_url: str = "",
    llm_api_key_env: str = "OPENAI_API_KEY",
    llm_client: LLMClient | None = None,
) -> WorkflowRun:
    out = Path(out_dir) if out_dir else Path("outputs/private") / _slug(Path(job_path).stem)
    out.mkdir(parents=True, exist_ok=True)

    intake = IntakeAgent()
    gate = DecisionGateAgent()
    reporter = ReportAgent()
    cv_planner = CVPlanAgent()
    next_actions = NextActionsAgent()
    memory_agent = MemoryAgent()
    llm_drafter = LLMDraftAgent()

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

    llm_cv_plan_path: Path | None = None
    llm_verification_path: Path | None = None
    should_attempt_llm = llm_client is not None or (llm_provider or "none").strip().lower() != "none"
    if cv_plan_path and should_attempt_llm:
        try:
            client = llm_client or build_llm_client(
                provider=llm_provider,
                model=llm_model,
                base_url=llm_base_url,
                api_key_env=llm_api_key_env,
            )
        except ValueError as exc:
            llm_verification_path = _write_llm_failure(out, str(exc), provider=llm_provider, model=llm_model)
        else:
            if client is not None:
                llm_cv_plan_path, llm_verification_path = llm_drafter.write(result, out, client)

    memory_written: Path | None = None
    if memory_path:
        memory_written = memory_agent.update(memory_path, result)

    next_actions_path = next_actions.write(status, result, out, cv_plan_path, llm_cv_plan_path, llm_verification_path)
    artifacts = WorkflowArtifacts(
        out_dir=out,
        report=report_path,
        decision=decision_path,
        next_actions=next_actions_path,
        cv_plan=cv_plan_path,
        llm_cv_plan=llm_cv_plan_path,
        llm_verification=llm_verification_path,
        memory=memory_written,
    )
    return WorkflowRun(status=status, result=result, artifacts=artifacts)


def _normalize_engine(engine: str) -> str:
    normalized = (engine or DEFAULT_WORKFLOW_ENGINE).strip().lower()
    if normalized not in WORKFLOW_ENGINES:
        allowed = ", ".join(sorted(WORKFLOW_ENGINES))
        raise ValueError(f"Unknown workflow engine: {engine}. Expected one of: {allowed}.")
    return normalized


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
        "negative_signals": [signal.model_dump() for signal in result.negative_signals],
        "root_strengths": result.root_matches,
        "interview_upskill": result.upskill_matches,
        "do_not_claim": result.irrelevant_or_low_signal,
        "gaps": result.gaps,
        "llm_policy": "Optional LLM drafts may assist wording only after the gate allows CV planning; they cannot override red lines or verifier failures.",
    }


def _next_actions(
    status: str,
    result: MatchResult,
    cv_plan_path: Path | None,
    llm_cv_plan_path: Path | None = None,
    llm_verification_path: Path | None = None,
) -> list[str]:
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
        if llm_cv_plan_path:
            lines.extend(
                [
                    "",
                    "## Optional LLM Draft Ready",
                    "",
                    f"- Review `{llm_cv_plan_path}` only as wording assistance.",
                    f"- Keep `{llm_verification_path}` with the application artifacts.",
                    "- The LLM draft cannot override the deterministic gate, red lines, or private evidence checks.",
                ]
            )
        elif llm_verification_path:
            lines.extend(
                [
                    "",
                    "## Optional LLM Draft Not Accepted",
                    "",
                    f"- Review `{llm_verification_path}` for the rejection or provider error.",
                    "- Use the deterministic CV plan instead.",
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


def _llm_verification_payload(verification: LLMVerification, provider: str, model: str) -> dict:
    payload = verification.model_dump()
    payload["provider"] = provider
    payload["model"] = model
    return payload


def _write_llm_failure(out_dir: Path, warning: str, provider: str, model: str) -> Path:
    path = out_dir / "llm_verification.json"
    payload = _llm_verification_payload(
        LLMVerification(
            passed=False,
            warnings=[warning],
            checked_rules=["provider configuration"],
        ),
        provider=provider or "unknown",
        model=model or "unknown",
    )
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
