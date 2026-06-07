from __future__ import annotations

import argparse
import base64
import json
import threading
import uuid
from pathlib import Path
from typing import TypeVar
from urllib.parse import urlparse

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from .api_models import (
    ArtifactResponse,
    BaseCVUploadRequest,
    BaseCVUploadResponse,
    HealthResponse,
    JobTextRequest,
    PathResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
    WorkflowResumeRequest,
    WorkspaceCreateRequest,
    WorkspaceCreateResponse,
)
from .workflow import (
    DEFAULT_WORKFLOW_ENGINE,
    WORKFLOW_ENGINES,
    WorkflowEngineError,
    run_workflow,
)


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_REQUEST_BYTES = 25_000_000
WORKFLOW_LOCK = threading.Lock()
PayloadModel = TypeVar("PayloadModel", bound=BaseModel)


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def build_app(workspace_root: str | Path = ".", web_root: str | Path = "web") -> FastAPI:
    root = Path(workspace_root).resolve()
    web = Path(web_root).resolve()
    app = FastAPI(
        title="Apply Less, Fit More Local API",
        version="0.1.0",
        responses={400: {"description": "Local API error"}, 404: {"description": "Not found"}},
    )
    app.state.workspace_root = root
    app.state.web_root = web
    app.state.workflow_checkpointer = _build_langgraph_checkpointer()

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$",
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def local_response_contract(request: Request, call_next):
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > MAX_REQUEST_BYTES:
                    return _error_response(413, "Request body is too large")
            except ValueError:
                return _error_response(400, "Invalid Content-Length")
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(_request: Request, exc: ApiError):
        return _error_response(exc.status, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError):
        return _error_response(400, _validation_message(exc))

    @app.get("/api/health", response_model=HealthResponse)
    async def health(request: Request):
        return {"ok": True, "workspace_root": str(request.app.state.workspace_root)}

    @app.get("/api/artifacts", response_model=ArtifactResponse)
    async def artifacts(request: Request, out_dir: str = Query("outputs/private")):
        return _read_artifacts(request.app.state.workspace_root, out_dir)

    @app.post("/api/jobs/text", response_model=PathResponse)
    async def jobs_text(request: Request, payload: JobTextRequest):
        return _write_job_text(request.app.state.workspace_root, payload)

    @app.post("/api/workspace/create", response_model=WorkspaceCreateResponse)
    async def workspace_create(request: Request, payload: WorkspaceCreateRequest):
        return _create_workspace(request.app.state.workspace_root, payload)

    @app.post("/api/files/base-cv", response_model=BaseCVUploadResponse)
    async def base_cv(request: Request, payload: BaseCVUploadRequest):
        return _write_base_cv(request.app.state.workspace_root, payload)

    @app.post("/api/workflows/run", response_model=WorkflowRunResponse)
    async def workflows_run(request: Request, payload: WorkflowRunRequest):
        return _run_workflow_api(
            request.app.state.workspace_root,
            payload,
            checkpointer=request.app.state.workflow_checkpointer,
        )

    @app.post("/api/workflows/resume", response_model=WorkflowRunResponse)
    async def workflows_resume(request: Request, payload: WorkflowResumeRequest):
        return _resume_workflow_api(
            request.app.state.workspace_root,
            payload,
            checkpointer=request.app.state.workflow_checkpointer,
        )

    @app.options("/{_path:path}", include_in_schema=False)
    async def options_any(_path: str):
        return Response(status_code=204)

    @app.api_route("/api/{_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    async def unknown_api(_path: str):
        raise ApiError(404, "Unknown API route")

    @app.get("/", include_in_schema=False)
    async def root_redirect():
        return RedirectResponse("/web/index.html")

    if web.is_dir():
        app.mount("/web", StaticFiles(directory=str(web)), name="web")

    return app


def build_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    workspace_root: str | Path = ".",
    web_root: str | Path = "web",
) -> FastAPI:
    if not _is_loopback_host(host):
        raise ValueError("Local backend must bind to localhost/127.0.0.1")
    return build_app(workspace_root=workspace_root, web_root=web_root)


def _error_response(status: int, message: str) -> JSONResponse:
    return JSONResponse({"ok": False, "error": message}, status_code=status)


def _validation_message(exc: RequestValidationError | ValidationError) -> str:
    errors = exc.errors()
    if not errors:
        return "Invalid request"
    first = errors[0]
    location = ".".join(str(item) for item in first.get("loc", []) if item != "body")
    prefix = f"{location}: " if location else ""
    return f"{prefix}{first.get('msg', 'Invalid request')}"


def _build_langgraph_checkpointer():
    try:
        from langgraph.checkpoint.memory import InMemorySaver
        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    except ImportError:
        return None
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


def _validate_payload(model: type[PayloadModel], payload: PayloadModel | dict) -> PayloadModel:
    if isinstance(payload, model):
        return payload
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ApiError(400, _validation_message(exc)) from exc


def _safe_path(root: Path, value: str) -> Path:
    if not value:
        raise ApiError(400, "Path is required")
    raw = Path(value).expanduser()
    path = raw if raw.is_absolute() else root / raw
    resolved = path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ApiError(400, f"Path must stay inside workspace: {value}") from exc
    return resolved


def _safe_job_path(root: Path, value: str) -> Path:
    path = _safe_path(root, value)
    _require_child(root, path, "inputs/jobs", "JD path must be under inputs/jobs/")
    if path.suffix.lower() not in {".txt", ".md"}:
        raise ApiError(400, "JD path must end in .txt or .md")
    return path


def _safe_profile_path(root: Path, value: str) -> Path:
    path = _safe_path(root, value)
    _require_child(root, path, "profiles", "Profile path must be under profiles/")
    if path.suffix.lower() != ".json":
        raise ApiError(400, "Profile path must end in .json")
    return path


def _safe_cv_path(root: Path, value: str) -> Path:
    path = _safe_path(root, value)
    _require_child(root, path, "private_resumes", "Baseline CV path must be under private_resumes/")
    if path.suffix.lower() not in {".pdf", ".docx", ".tex", ".md", ".txt"}:
        raise ApiError(400, "Baseline CV path must be .pdf, .docx, .tex, .md, or .txt")
    return path


def _safe_output_dir(root: Path, value: str) -> Path:
    path = _safe_path(root, value)
    _require_child(root, path, "outputs/private", "Output directory must be under outputs/private/")
    return path


def _safe_memory_path(root: Path, value: str) -> Path:
    path = _safe_path(root, value)
    if not path.name.endswith(".local.json"):
        raise ApiError(400, "Memory path must end in .local.json")
    return path


def _require_child(root: Path, path: Path, prefix: str, message: str) -> None:
    allowed = (root / prefix).resolve()
    try:
        path.resolve().relative_to(allowed)
    except ValueError as exc:
        raise ApiError(400, message) from exc


def _validate_workflow_engine(value: object) -> str:
    engine = str(value or DEFAULT_WORKFLOW_ENGINE).strip().lower()
    if engine not in WORKFLOW_ENGINES:
        allowed = ", ".join(sorted(WORKFLOW_ENGINES))
        raise ApiError(400, f"Workflow engine must be one of: {allowed}")
    return engine


def _is_loopback_host(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


def _validate_llm_base_url(provider: str, base_url: str) -> None:
    if provider != "openai-compatible" or not base_url:
        return
    host = urlparse(base_url).hostname or ""
    if not _is_loopback_host(host):
        raise ApiError(400, "LLM base URL must be localhost/127.0.0.1 in local backend mode")


def _relative_display(root: Path, path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _read_text(path: Path | None) -> str:
    if path and path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _read_json_file(path: Path | None) -> dict | None:
    if not path or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"_error": f"Could not parse JSON: {exc}"}


def _artifact_payload(root: Path, out_dir: Path, artifacts: dict[str, Path | None]) -> dict:
    return {
        "out_dir": _relative_display(root, out_dir),
        "paths": {name: _relative_display(root, path) for name, path in artifacts.items()},
        "decision": _read_json_file(artifacts.get("decision")),
        "report": _read_text(artifacts.get("report")),
        "next_actions": _read_text(artifacts.get("next_actions")),
        "cv_plan": _read_text(artifacts.get("cv_plan")),
        "llm_cv_plan": _read_text(artifacts.get("llm_cv_plan")),
        "llm_verification": _read_json_file(artifacts.get("llm_verification")),
    }


def _read_artifacts(root: Path, out_dir_value: str) -> dict:
    out_dir = _safe_output_dir(root, out_dir_value)
    artifacts = {
        "decision": out_dir / "decision.json",
        "report": out_dir / "report.md",
        "next_actions": out_dir / "next_actions.md",
        "cv_plan": out_dir / "cv_plan.md",
        "llm_cv_plan": out_dir / "cv_plan.llm.md",
        "llm_verification": out_dir / "llm_verification.json",
    }
    return {"ok": True, "artifacts": _artifact_payload(root, out_dir, artifacts)}


def _write_job_text(root: Path, payload: JobTextRequest | dict) -> dict:
    request = _validate_payload(JobTextRequest, payload)
    path_value = request.job_path or request.path or "inputs/jobs/job.txt"
    content = request.content if request.content is not None else request.text
    path = _safe_job_path(root, str(path_value))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(content or ""), encoding="utf-8")
    return {"ok": True, "path": _relative_display(root, path)}


def _create_workspace(root: Path, payload: WorkspaceCreateRequest | dict) -> dict:
    request = _validate_payload(WorkspaceCreateRequest, payload)
    job_path = _safe_job_path(root, request.job_path)
    profile_path = _safe_profile_path(root, request.profile_path)
    cv_path_value = request.cv_path or request.initial_cv_path or request.path or "private_resumes/base_cv.pdf"
    cv_path = _safe_cv_path(root, cv_path_value)
    memory_path = _safe_memory_path(root, request.memory_path)
    out_dir = _safe_output_dir(root, request.out_dir)
    for path in [job_path.parent, profile_path.parent, cv_path.parent, memory_path.parent, out_dir]:
        path.mkdir(parents=True, exist_ok=True)
    if not memory_path.exists():
        memory_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "applications": [],
                    "learned_filters": [],
                    "recurring_red_lines": [],
                    "do_not_claim": [],
                    "notes": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if not profile_path.exists():
        profile_path.write_text(_starter_profile(), encoding="utf-8")
    return {
        "ok": True,
        "created": {
            "job_dir": _relative_display(root, job_path.parent),
            "profile": _relative_display(root, profile_path),
            "cv_dir": _relative_display(root, cv_path.parent),
            "memory": _relative_display(root, memory_path),
            "out_dir": _relative_display(root, out_dir),
        },
    }


def _write_base_cv(root: Path, payload: BaseCVUploadRequest | dict) -> dict:
    request = _validate_payload(BaseCVUploadRequest, payload)
    cv_path_value = request.cv_path or request.initial_cv_path or request.path or "private_resumes/base_cv.pdf"
    cv_path = _safe_cv_path(root, cv_path_value)
    if not request.content_base64:
        raise ApiError(400, "content_base64 is required")
    try:
        data = base64.b64decode(request.content_base64, validate=True)
    except ValueError as exc:
        raise ApiError(400, "content_base64 is not valid base64") from exc
    cv_path.parent.mkdir(parents=True, exist_ok=True)
    cv_path.write_bytes(data)
    return {"ok": True, "path": _relative_display(root, cv_path), "bytes": len(data)}


def _starter_profile() -> str:
    return json.dumps(
        {
            "name": "EDIT_ME_PRIVATE",
            "headline": "Private local profile draft. Replace before running real workflows.",
            "target_roles": [],
            "locations": [],
            "market_facts": {
                "work_authorization": "ask locally before claiming",
                "commute_or_relocation": "ask locally before claiming",
                "mandatory_internship_proof": "ask locally before claiming",
            },
            "ability_model": {
                "root_strengths": [],
                "interview_upskill": [],
                "irrelevant_or_low_signal": [],
                "negative_ability_red_lines": [
                    "Do not claim mandatory internship eligibility without private proof.",
                    "Do not treat an unverified commute as solved.",
                    "Do not rewrite projects into unrelated domains without direct evidence.",
                ],
            },
            "education": [],
            "skills": {},
            "experiences": [],
            "projects": [],
            "languages": [],
        },
        indent=2,
        ensure_ascii=False,
    ) + "\n"


def _run_workflow_api(root: Path, payload: WorkflowRunRequest | dict, checkpointer=None) -> dict:
    request = _validate_payload(WorkflowRunRequest, payload)
    job_path = _safe_job_path(root, request.job_path)
    profile_path = _safe_profile_path(root, request.profile_path)
    out_dir = _safe_output_dir(root, request.out_dir or f"outputs/private/{job_path.stem}")
    memory_raw = str(request.memory_path or "").strip()
    memory_path = _safe_memory_path(root, memory_raw) if memory_raw else None
    if not job_path.exists():
        raise ApiError(400, f"JD file not found: {_relative_display(root, job_path)}")
    if not profile_path.exists():
        raise ApiError(400, f"Profile file not found: {_relative_display(root, profile_path)}")

    engine = _validate_workflow_engine(request.engine)
    _validate_llm_base_url(request.llm_provider, request.llm_base_url)
    thread_id = request.thread_id or _new_workflow_thread_id()
    run_kwargs = {
        "job_path": job_path,
        "profile_path": profile_path,
        "out_dir": out_dir,
        "memory_path": memory_path,
        "company": request.company,
        "title": request.title,
        "auto_approve": request.auto_approve,
        "input_fn": (lambda _prompt: "n"),
        "llm_provider": request.llm_provider,
        "llm_model": request.llm_model,
        "llm_base_url": request.llm_base_url,
        "llm_api_key_env": request.llm_api_key_env,
        "engine": engine,
        "thread_id": thread_id if engine == "langgraph" else None,
        "checkpointer": checkpointer if engine == "langgraph" else None,
    }
    with WORKFLOW_LOCK:
        try:
            run = run_workflow(**run_kwargs)
        except WorkflowEngineError as exc:
            raise ApiError(400, str(exc)) from exc
    return _workflow_response(root, run, engine)


def _resume_workflow_api(root: Path, payload: WorkflowResumeRequest | dict, checkpointer=None) -> dict:
    request = _validate_payload(WorkflowResumeRequest, payload)
    if not checkpointer:
        raise ApiError(400, "No active LangGraph checkpointer is available. Restart the workflow run.")
    resume_payload = {
        "approved": request.approved,
        "comment": request.comment,
        "checkpoint_id": request.checkpoint_id,
        "checkpoint_kind": request.checkpoint_kind,
    }
    with WORKFLOW_LOCK:
        try:
            from .langgraph_workflow import resume_langgraph_workflow

            run = resume_langgraph_workflow(
                thread_id=request.thread_id,
                checkpointer=checkpointer,
                resume=resume_payload,
            )
        except WorkflowEngineError as exc:
            raise ApiError(400, str(exc)) from exc
        except KeyError as exc:
            raise ApiError(400, "Workflow checkpoint could not be resumed. Start a new workflow run.") from exc
        except ValueError as exc:
            raise ApiError(400, str(exc)) from exc
    return _workflow_response(root, run, "langgraph")


def _workflow_response(root: Path, run, engine: str) -> dict:
    artifacts = {
        "decision": run.artifacts.decision,
        "report": run.artifacts.report,
        "next_actions": run.artifacts.next_actions,
        "cv_plan": run.artifacts.cv_plan,
        "llm_cv_plan": run.artifacts.llm_cv_plan,
        "llm_verification": run.artifacts.llm_verification,
        "memory": run.artifacts.memory,
    }
    pending_checkpoint = run.pending_checkpoint.model_dump() if run.pending_checkpoint else None
    return {
        "ok": True,
        "status": run.status,
        "engine": engine,
        "thread_id": run.thread_id,
        "pending": pending_checkpoint is not None,
        "pending_checkpoint": pending_checkpoint,
        "artifacts": _artifact_payload(root, run.artifacts.out_dir, artifacts),
    }


def _new_workflow_thread_id() -> str:
    return "workflow-" + uuid.uuid4().hex


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the local job-agent web UI and API")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--web-root", default="web")
    args = parser.parse_args(argv)
    if not _is_loopback_host(args.host):
        raise ValueError("Local backend must bind to localhost/127.0.0.1")

    app = build_app(workspace_root=args.workspace, web_root=args.web_root)
    print(f"Serving job-agent UI: http://{args.host}:{args.port}/web/index.html")
    print(f"Workspace root: {Path(args.workspace).resolve()}")
    try:
        import uvicorn
    except ImportError as exc:
        raise WorkflowEngineError("FastAPI server requires uvicorn. Install with: pip install -e .") from exc
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
