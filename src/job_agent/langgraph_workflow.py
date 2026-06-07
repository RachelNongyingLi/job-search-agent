from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from .llm import LLMProviderError, build_llm_client
from .workflow import (
    CVPlanAgent,
    DecisionGateAgent,
    IntakeAgent,
    LLMDraftAgent,
    MemoryAgent,
    NextActionsAgent,
    ReportAgent,
    WorkflowArtifacts,
    WorkflowEngineError,
    WorkflowRun,
    _confirm,
    _slug,
    _write_llm_failure,
)


class WorkflowState(TypedDict, total=False):
    job_path: str | Path
    profile_path: str | Path
    out_dir: Path
    memory_path: str | Path | None
    company: str
    title: str
    auto_approve: bool
    input_fn: Any
    llm_provider: str
    llm_model: str
    llm_base_url: str
    llm_api_key_env: str
    llm_client: Any
    profile: Any
    job: Any
    result: Any
    status: str
    report_path: Path
    decision_path: Path
    cv_plan_path: Path | None
    llm_cv_plan_path: Path | None
    llm_verification_path: Path | None
    memory_written: Path | None
    next_actions_path: Path


def run_langgraph_workflow(
    job_path: str | Path,
    profile_path: str | Path,
    out_dir: str | Path | None = None,
    memory_path: str | Path | None = None,
    company: str = "",
    title: str = "",
    auto_approve: bool = False,
    input_fn: Any = input,
    llm_provider: str = "none",
    llm_model: str = "",
    llm_base_url: str = "",
    llm_api_key_env: str = "OPENAI_API_KEY",
    llm_client: Any = None,
) -> WorkflowRun:
    out = Path(out_dir) if out_dir else Path("outputs/private") / _slug(Path(job_path).stem)
    out.mkdir(parents=True, exist_ok=True)

    graph = _compile_graph()
    final = graph.invoke(
        {
            "job_path": job_path,
            "profile_path": profile_path,
            "out_dir": out,
            "memory_path": memory_path,
            "company": company,
            "title": title,
            "auto_approve": auto_approve,
            "input_fn": input_fn,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "llm_base_url": llm_base_url,
            "llm_api_key_env": llm_api_key_env,
            "llm_client": llm_client,
        }
    )
    artifacts = WorkflowArtifacts(
        out_dir=out,
        report=final["report_path"],
        decision=final["decision_path"],
        next_actions=final["next_actions_path"],
        cv_plan=final.get("cv_plan_path"),
        llm_cv_plan=final.get("llm_cv_plan_path"),
        llm_verification=final.get("llm_verification_path"),
        memory=final.get("memory_written"),
    )
    return WorkflowRun(status=final["status"], result=final["result"], artifacts=artifacts)


def _compile_graph():
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:
        raise WorkflowEngineError("LangGraph engine requires project dependencies. Install with: pip install -e .") from exc

    graph = StateGraph(WorkflowState)
    graph.add_node("intake", _intake_node)
    graph.add_node("gate", _gate_node)
    graph.add_node("report", _report_node)
    graph.add_node("cv_plan", _cv_plan_node)
    graph.add_node("llm_draft", _llm_draft_node)
    graph.add_node("memory", _memory_node)
    graph.add_node("next_actions", _next_actions_node)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "gate")
    graph.add_edge("gate", "report")
    graph.add_conditional_edges("report", _after_report, {"cv_plan": "cv_plan", "memory": "memory"})
    graph.add_conditional_edges("cv_plan", _after_cv_plan, {"llm_draft": "llm_draft", "memory": "memory"})
    graph.add_edge("llm_draft", "memory")
    graph.add_edge("memory", "next_actions")
    graph.add_edge("next_actions", END)
    return graph.compile()


def _intake_node(state: WorkflowState) -> WorkflowState:
    profile, job = IntakeAgent().load(
        state["job_path"],
        state["profile_path"],
        company=state.get("company", ""),
        title=state.get("title", ""),
    )
    return {"profile": profile, "job": job}


def _gate_node(state: WorkflowState) -> WorkflowState:
    gate = DecisionGateAgent()
    result = gate.evaluate(state["profile"], state["job"])
    return {"result": result, "status": gate.status(result)}


def _report_node(state: WorkflowState) -> WorkflowState:
    report_path, decision_path = ReportAgent().write(state["profile"], state["result"], state["out_dir"])
    return {"report_path": report_path, "decision_path": decision_path}


def _cv_plan_node(state: WorkflowState) -> WorkflowState:
    status = state["status"]
    result = state["result"]
    should_write = False
    if status == "needs_verification":
        should_write = _confirm(
            "This role needs verification before CV tailoring. Generate a cautious CV plan anyway?",
            default=False,
            auto_approve=state.get("auto_approve", False),
            input_fn=state.get("input_fn", input),
        )
    elif status in {"ready_for_cv_plan", "selective_cv_plan"}:
        should_write = _confirm(
            "Generate CV targeting plan?",
            default=True,
            auto_approve=state.get("auto_approve", False),
            input_fn=state.get("input_fn", input),
        )
    if not should_write:
        return {"cv_plan_path": None}
    return {"cv_plan_path": CVPlanAgent().write(result, state["out_dir"])}


def _llm_draft_node(state: WorkflowState) -> WorkflowState:
    try:
        client = state.get("llm_client") or build_llm_client(
            provider=state.get("llm_provider", "none"),
            model=state.get("llm_model", ""),
            base_url=state.get("llm_base_url", ""),
            api_key_env=state.get("llm_api_key_env", "OPENAI_API_KEY"),
        )
    except ValueError as exc:
        return {
            "llm_cv_plan_path": None,
            "llm_verification_path": _write_llm_failure(
                state["out_dir"],
                str(exc),
                provider=state.get("llm_provider", "none"),
                model=state.get("llm_model", ""),
            ),
        }
    if client is None:
        return {"llm_cv_plan_path": None, "llm_verification_path": None}
    try:
        draft_path, verification_path = LLMDraftAgent().write(state["result"], state["out_dir"], client)
    except LLMProviderError as exc:
        return {
            "llm_cv_plan_path": None,
            "llm_verification_path": _write_llm_failure(
                state["out_dir"],
                str(exc),
                provider=getattr(client, "provider", "unknown"),
                model=getattr(client, "model", "unknown"),
            ),
        }
    return {"llm_cv_plan_path": draft_path, "llm_verification_path": verification_path}


def _memory_node(state: WorkflowState) -> WorkflowState:
    memory_path = state.get("memory_path")
    if not memory_path:
        return {"memory_written": None}
    return {"memory_written": MemoryAgent().update(memory_path, state["result"])}


def _next_actions_node(state: WorkflowState) -> WorkflowState:
    next_actions_path = NextActionsAgent().write(
        state["status"],
        state["result"],
        state["out_dir"],
        state.get("cv_plan_path"),
        state.get("llm_cv_plan_path"),
        state.get("llm_verification_path"),
    )
    return {"next_actions_path": next_actions_path}


def _after_report(state: WorkflowState) -> str:
    if state["status"] == "red_line_block":
        return "memory"
    return "cv_plan"


def _after_cv_plan(state: WorkflowState) -> str:
    if state.get("cv_plan_path") and _should_attempt_llm(state):
        return "llm_draft"
    return "memory"


def _should_attempt_llm(state: WorkflowState) -> bool:
    return state.get("llm_client") is not None or (state.get("llm_provider") or "none").strip().lower() != "none"
