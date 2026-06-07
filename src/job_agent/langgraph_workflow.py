from __future__ import annotations

import uuid
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
    WorkflowCheckpoint,
    WorkflowEngineError,
    WorkflowRun,
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
    cv_plan_approved: bool
    public_output_path: Path | None
    public_output_approved: bool
    final_pdf_path: Path | None
    final_pdf_approved: bool
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
    thread_id: str | None = None,
    checkpointer: Any = None,
    resume: Any = None,
) -> WorkflowRun:
    out = Path(out_dir) if out_dir else Path("outputs/private") / _slug(Path(job_path).stem)
    out.mkdir(parents=True, exist_ok=True)

    if not thread_id and not auto_approve:
        thread_id = "workflow-" + uuid.uuid4().hex
    if thread_id and checkpointer is None:
        checkpointer = _memory_checkpointer()
    graph = _compile_graph(checkpointer=checkpointer)
    config = _thread_config(thread_id)
    if resume is not None:
        try:
            from langgraph.types import Command
        except ImportError as exc:
            raise WorkflowEngineError("LangGraph resume requires project dependencies. Install with: pip install -e .") from exc
        graph_input: Any = Command(resume=resume)
    else:
        graph_input = {
            "job_path": job_path,
            "profile_path": profile_path,
            "out_dir": out,
            "memory_path": memory_path,
            "company": company,
            "title": title,
            "auto_approve": auto_approve,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "llm_base_url": llm_base_url,
            "llm_api_key_env": llm_api_key_env,
            "llm_client": llm_client if checkpointer is None else None,
        }
    final = graph.invoke(graph_input, config=config) if config else graph.invoke(graph_input)
    return _workflow_run_from_state(final, thread_id=thread_id)


def resume_langgraph_workflow(
    thread_id: str,
    checkpointer: Any,
    resume: Any,
) -> WorkflowRun:
    return run_langgraph_workflow(
        job_path="__resume__",
        profile_path="__resume__",
        thread_id=thread_id,
        checkpointer=checkpointer,
        resume=resume,
    )


def _compile_graph(checkpointer: Any = None):
    try:
        from langgraph.graph import END, StateGraph
    except ImportError as exc:
        raise WorkflowEngineError("LangGraph engine requires project dependencies. Install with: pip install -e .") from exc

    graph = StateGraph(WorkflowState)
    graph.add_node("intake", _intake_node)
    graph.add_node("gate", _gate_node)
    graph.add_node("report", _report_node)
    graph.add_node("cv_plan_checkpoint", _cv_plan_checkpoint_node)
    graph.add_node("cv_plan", _cv_plan_node)
    graph.add_node("llm_draft", _llm_draft_node)
    graph.add_node("public_output_checkpoint", _public_output_checkpoint_node)
    graph.add_node("final_pdf_checkpoint", _final_pdf_checkpoint_node)
    graph.add_node("memory", _memory_node)
    graph.add_node("next_actions", _next_actions_node)

    graph.set_entry_point("intake")
    graph.add_edge("intake", "gate")
    graph.add_edge("gate", "report")
    graph.add_conditional_edges("report", _after_report, {"cv_plan_checkpoint": "cv_plan_checkpoint", "memory": "memory"})
    graph.add_edge("cv_plan_checkpoint", "cv_plan")
    graph.add_conditional_edges("cv_plan", _after_cv_plan, {"llm_draft": "llm_draft", "public_output_checkpoint": "public_output_checkpoint"})
    graph.add_edge("llm_draft", "public_output_checkpoint")
    graph.add_edge("public_output_checkpoint", "final_pdf_checkpoint")
    graph.add_edge("final_pdf_checkpoint", "memory")
    graph.add_edge("memory", "next_actions")
    graph.add_edge("next_actions", END)
    return graph.compile(checkpointer=checkpointer)


def _memory_checkpointer():
    try:
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    except ImportError as exc:
        raise WorkflowEngineError("LangGraph checkpointing requires project dependencies. Install with: pip install -e .") from exc
    serializer = JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("job_agent.models", "CandidateProfile"),
            ("job_agent.models", "JobAnalysis"),
            ("job_agent.models", "MatchResult"),
            ("job_agent.models", "Evidence"),
            ("job_agent.models", "NegativeSignal"),
        ]
    )
    return InMemorySaver(serde=serializer)


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


def _cv_plan_checkpoint_node(state: WorkflowState) -> WorkflowState:
    status = state["status"]
    if status == "red_line_block":
        return {"cv_plan_approved": False}
    if state.get("auto_approve", False):
        return {"cv_plan_approved": True}

    payload = _checkpoint_payload(
        kind="cv_plan_approval",
        title="Approve CV plan generation",
        message="The fit gate has completed. Confirm before writing cv_plan.md or allowing any later CV wording work.",
        action="approve_cv_plan",
        state=state,
        requires=[
            "Review decision.json and report.md first.",
            "Every future CV bullet must have evidence in profile, project, current CV, or report.",
            "Do not approve if eligibility, commute, relocation, language, or authorization facts are unsafe to state.",
        ],
    )
    approved = _interrupt_for_approval(payload)
    return {"cv_plan_approved": approved}


def _cv_plan_node(state: WorkflowState) -> WorkflowState:
    if not state.get("cv_plan_approved", False):
        return {"cv_plan_path": None}
    return {"cv_plan_path": CVPlanAgent().write(state["result"], state["out_dir"])}


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


def _public_output_checkpoint_node(state: WorkflowState) -> WorkflowState:
    public_output_path = state.get("public_output_path")
    if not public_output_path:
        return {"public_output_approved": False}
    if state.get("auto_approve", False):
        return {"public_output_approved": True}
    payload = _checkpoint_payload(
        kind="public_output_approval",
        title="Approve public application wording",
        message="Confirm before private evidence becomes public wording in a CV, cover letter, or recruiter message.",
        action="approve_public_output",
        state=state,
        requires=[
            "Every public claim must be evidence-backed.",
            "No private eligibility, authorization, location, or language fact may be exposed unless safe.",
            "A red-line block means no public wording should be produced.",
        ],
    )
    return {"public_output_approved": _interrupt_for_approval(payload)}


def _final_pdf_checkpoint_node(state: WorkflowState) -> WorkflowState:
    final_pdf_path = state.get("final_pdf_path")
    if not final_pdf_path:
        return {"final_pdf_approved": False}
    if state.get("auto_approve", False):
        return {"final_pdf_approved": True}
    payload = _checkpoint_payload(
        kind="final_pdf_approval",
        title="Approve final one-page PDF",
        message="Confirm only after the LaTeX CV compiles cleanly and the final PDF is exactly one page.",
        action="approve_final_pdf",
        state=state,
        requires=[
            "LaTeX compilation succeeded without layout-breaking errors.",
            "The final CV PDF is exactly one page.",
            "The final PDF has no unsupported bullets, private leakage, or red-line violations.",
        ],
    )
    return {"final_pdf_approved": _interrupt_for_approval(payload)}


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
    return "cv_plan_checkpoint"


def _after_cv_plan(state: WorkflowState) -> str:
    if state.get("cv_plan_path") and _should_attempt_llm(state):
        return "llm_draft"
    return "public_output_checkpoint"


def _should_attempt_llm(state: WorkflowState) -> bool:
    return state.get("llm_client") is not None or (state.get("llm_provider") or "none").strip().lower() != "none"


def _thread_config(thread_id: str | None) -> dict | None:
    if not thread_id:
        return None
    return {"configurable": {"thread_id": thread_id}}


def _interrupt_for_approval(payload: dict) -> bool:
    try:
        from langgraph.types import interrupt
    except ImportError as exc:
        raise WorkflowEngineError("LangGraph interrupt requires project dependencies. Install with: pip install -e .") from exc

    response = interrupt(payload)
    if isinstance(response, dict):
        return bool(response.get("approved", False))
    return bool(response)


def _checkpoint_payload(
    kind: str,
    title: str,
    message: str,
    action: str,
    state: WorkflowState,
    requires: list[str],
) -> dict:
    result = state["result"]
    return {
        "kind": kind,
        "title": title,
        "message": message,
        "action": action,
        "risk_level": "human_required",
        "requires": requires,
        "state_summary": {
            "workflow_status": state.get("status", ""),
            "score": result.score,
            "decision": result.decision,
            "company": result.job.company,
            "role": result.job.title,
            "red_lines": [signal.suggested_action for signal in result.negative_signals if signal.severity == "block"],
            "market_risks": result.market_risks,
            "report_path": str(state.get("report_path", "")),
            "decision_path": str(state.get("decision_path", "")),
        },
    }


def _workflow_run_from_state(final: dict, thread_id: str | None) -> WorkflowRun:
    checkpoint = _pending_checkpoint(final)
    artifacts = WorkflowArtifacts(
        out_dir=final.get("out_dir") or Path("outputs/private"),
        report=final.get("report_path"),
        decision=final.get("decision_path"),
        next_actions=final.get("next_actions_path"),
        cv_plan=final.get("cv_plan_path"),
        llm_cv_plan=final.get("llm_cv_plan_path"),
        llm_verification=final.get("llm_verification_path"),
        memory=final.get("memory_written"),
    )
    return WorkflowRun(
        status=final.get("status", "pending_checkpoint"),
        result=final["result"],
        artifacts=artifacts,
        pending_checkpoint=checkpoint,
        thread_id=thread_id,
    )


def _pending_checkpoint(final: dict) -> WorkflowCheckpoint | None:
    interrupts = final.get("__interrupt__") or []
    if not interrupts:
        return None
    interrupt_item = interrupts[0]
    value = getattr(interrupt_item, "value", interrupt_item)
    if not isinstance(value, dict):
        value = {
            "kind": "human_checkpoint",
            "title": "Human checkpoint",
            "message": str(value),
            "action": "approve",
        }
    payload = dict(value)
    payload["id"] = getattr(interrupt_item, "id", payload.get("id"))
    return WorkflowCheckpoint.model_validate(payload)
