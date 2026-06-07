from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, StrictBool


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JobTextRequest(ApiModel):
    job_path: str | None = None
    path: str | None = None
    content: str | None = None
    text: str | None = None


class WorkspaceCreateRequest(ApiModel):
    job_path: str = "inputs/jobs/job.txt"
    profile_path: str = "profiles/me.local.json"
    cv_path: str | None = None
    initial_cv_path: str | None = None
    path: str | None = None
    out_dir: str = "outputs/private/default"
    memory_path: str = "memory.local.json"


class BaseCVUploadRequest(ApiModel):
    cv_path: str | None = None
    initial_cv_path: str | None = None
    path: str | None = None
    content_base64: str


class WorkflowRunRequest(ApiModel):
    job_path: str
    profile_path: str = "profiles/me.local.json"
    out_dir: str | None = None
    memory_path: str | None = None
    company: str = ""
    title: str = ""
    auto_approve: StrictBool = False
    engine: Literal["langgraph", "classic"] = "langgraph"
    llm_provider: Literal["none", "mock", "openai-compatible"] = "none"
    llm_model: str = ""
    llm_base_url: str = ""
    llm_api_key_env: str = "OPENAI_API_KEY"


class HealthResponse(ApiModel):
    ok: bool
    workspace_root: str


class PathResponse(ApiModel):
    ok: bool
    path: str | None


class BaseCVUploadResponse(PathResponse):
    bytes: int


class WorkspaceCreated(ApiModel):
    job_dir: str | None
    profile: str | None
    cv_dir: str | None
    memory: str | None
    out_dir: str | None


class WorkspaceCreateResponse(ApiModel):
    ok: bool
    created: WorkspaceCreated


class ArtifactPayload(ApiModel):
    out_dir: str | None
    paths: dict[str, str | None]
    decision: dict[str, Any] | None
    report: str
    next_actions: str
    cv_plan: str
    llm_cv_plan: str
    llm_verification: dict[str, Any] | None


class ArtifactResponse(ApiModel):
    ok: bool
    artifacts: ArtifactPayload


class WorkflowRunResponse(ApiModel):
    ok: bool
    status: str
    engine: Literal["langgraph", "classic"]
    artifacts: ArtifactPayload


class ErrorResponse(ApiModel):
    ok: bool = False
    error: str
