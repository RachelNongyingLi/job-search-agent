from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .workflow import run_workflow


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
WORKFLOW_LOCK = threading.Lock()


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class LocalJobAgentServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], handler_class: type[BaseHTTPRequestHandler], workspace_root: Path, web_root: Path):
        super().__init__(server_address, handler_class)
        self.workspace_root = workspace_root.resolve()
        self.web_root = web_root.resolve()


class LocalJobAgentHandler(BaseHTTPRequestHandler):
    server_version = "JobAgentLocal/0.1"

    def do_OPTIONS(self) -> None:
        self._send_empty(204)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._send_json({"ok": True, "workspace_root": str(self.server.workspace_root)})
            return
        if parsed.path == "/api/artifacts":
            try:
                query = parse_qs(parsed.query)
                out_dir = _first(query, "out_dir") or "outputs/private"
                self._send_json(_read_artifacts(self.server.workspace_root, out_dir))
            except ApiError as exc:
                self._send_error(exc.status, exc.message)
            except Exception as exc:  # pragma: no cover - defensive boundary
                self._send_error(500, str(exc))
            return
        self._serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/jobs/text":
                payload = self._read_json()
                path_value = payload.get("job_path") or payload.get("path") or "inputs/jobs/job.txt"
                content = payload.get("content")
                if content is None:
                    content = payload.get("text")
                path = _safe_job_path(self.server.workspace_root, str(path_value))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(str(content or ""), encoding="utf-8")
                self._send_json({"ok": True, "path": _relative_display(self.server.workspace_root, path)})
                return
            if parsed.path == "/api/workspace/create":
                payload = self._read_json()
                self._send_json(_create_workspace(self.server.workspace_root, payload))
                return
            if parsed.path == "/api/files/base-cv":
                payload = self._read_json()
                self._send_json(_write_base_cv(self.server.workspace_root, payload))
                return
            if parsed.path == "/api/workflows/run":
                payload = self._read_json()
                self._send_json(_run_workflow_api(self.server.workspace_root, payload))
                return
            raise ApiError(404, "Unknown API route")
        except ApiError as exc:
            self._send_error(exc.status, exc.message)
        except Exception as exc:  # pragma: no cover - defensive boundary
            self._send_error(500, str(exc))

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError as exc:
            raise ApiError(400, "Invalid Content-Length") from exc
        if length > 25_000_000:
            raise ApiError(413, "Request body is too large")
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ApiError(400, f"Invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise ApiError(400, "Request body must be a JSON object")
        return payload

    def _serve_static(self, request_path: str) -> None:
        path = request_path if request_path not in {"", "/"} else "/web/index.html"
        if path.startswith("/web/"):
            target = _safe_path(self.server.web_root.parent, path.lstrip("/"))
        else:
            self._send_error(404, "Not found")
            return
        if not target.is_file():
            self._send_error(404, "Not found")
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(200)
        self._common_headers(content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self._common_headers("application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self._common_headers("text/plain; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_error(self, status: int, message: str) -> None:
        self._send_json({"ok": False, "error": message}, status=status)

    def _common_headers(self, content_type: str) -> None:
        self.send_header("Content-Type", content_type)
        origin = self.headers.get("Origin")
        if origin and _is_local_origin(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")


def _first(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or []
    return values[0] if values else ""


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


def _parse_bool(payload: dict, key: str, default: bool = False) -> bool:
    if key not in payload:
        return default
    value = payload[key]
    if isinstance(value, bool):
        return value
    raise ApiError(400, f"{key} must be a boolean")


def _is_local_origin(origin: str) -> bool:
    parsed = urlparse(origin)
    return parsed.scheme in {"http", "https"} and _is_loopback_host(parsed.hostname or "")


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


def _create_workspace(root: Path, payload: dict) -> dict:
    job_path = _safe_job_path(root, str(payload.get("job_path") or "inputs/jobs/job.txt"))
    profile_path = _safe_profile_path(root, str(payload.get("profile_path") or "profiles/me.local.json"))
    cv_path_value = payload.get("cv_path") or payload.get("initial_cv_path") or payload.get("path") or "private_resumes/base_cv.pdf"
    cv_path = _safe_cv_path(root, str(cv_path_value))
    memory_path = _safe_memory_path(root, str(payload.get("memory_path") or "memory.local.json"))
    out_dir = _safe_output_dir(root, str(payload.get("out_dir") or "outputs/private/default"))
    for path in [job_path.parent, profile_path.parent, cv_path.parent, memory_path.parent, out_dir]:
        path.mkdir(parents=True, exist_ok=True)
    if not memory_path.exists():
        memory_path.write_text(json.dumps({"version": 1, "applications": [], "learned_filters": [], "recurring_red_lines": [], "do_not_claim": [], "notes": []}, indent=2) + "\n", encoding="utf-8")
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


def _write_base_cv(root: Path, payload: dict) -> dict:
    cv_path_value = payload.get("cv_path") or payload.get("initial_cv_path") or payload.get("path") or "private_resumes/base_cv.pdf"
    cv_path = _safe_cv_path(root, str(cv_path_value))
    raw = str(payload.get("content_base64") or "")
    if not raw:
        raise ApiError(400, "content_base64 is required")
    try:
        data = base64.b64decode(raw, validate=True)
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


def _run_workflow_api(root: Path, payload: dict) -> dict:
    job_path = _safe_job_path(root, str(payload.get("job_path") or ""))
    profile_path = _safe_profile_path(root, str(payload.get("profile_path") or "profiles/me.local.json"))
    out_dir = _safe_output_dir(root, str(payload.get("out_dir") or f"outputs/private/{job_path.stem}"))
    memory_raw = str(payload.get("memory_path") or "").strip()
    memory_path = _safe_memory_path(root, memory_raw) if memory_raw else None
    if not job_path.exists():
        raise ApiError(400, f"JD file not found: {_relative_display(root, job_path)}")
    if not profile_path.exists():
        raise ApiError(400, f"Profile file not found: {_relative_display(root, profile_path)}")

    auto_approve = _parse_bool(payload, "auto_approve", default=False)
    llm_provider = str(payload.get("llm_provider") or "none")
    llm_base_url = str(payload.get("llm_base_url") or "")
    _validate_llm_base_url(llm_provider, llm_base_url)
    run_kwargs = {
        "job_path": job_path,
        "profile_path": profile_path,
        "out_dir": out_dir,
        "memory_path": memory_path,
        "company": str(payload.get("company") or ""),
        "title": str(payload.get("title") or ""),
        "auto_approve": auto_approve,
        "input_fn": (lambda _prompt: "n"),
        "llm_provider": llm_provider,
        "llm_model": str(payload.get("llm_model") or ""),
        "llm_base_url": llm_base_url,
        "llm_api_key_env": str(payload.get("llm_api_key_env") or "OPENAI_API_KEY"),
    }
    with WORKFLOW_LOCK:
        run = run_workflow(**run_kwargs)
    artifacts = {
        "decision": run.artifacts.decision,
        "report": run.artifacts.report,
        "next_actions": run.artifacts.next_actions,
        "cv_plan": run.artifacts.cv_plan,
        "llm_cv_plan": run.artifacts.llm_cv_plan,
        "llm_verification": run.artifacts.llm_verification,
        "memory": run.artifacts.memory,
    }
    return {
        "ok": True,
        "status": run.status,
        "artifacts": _artifact_payload(root, run.artifacts.out_dir, artifacts),
    }


def build_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, workspace_root: str | Path = ".", web_root: str | Path = "web") -> LocalJobAgentServer:
    if not _is_loopback_host(host):
        raise ValueError("Local backend must bind to localhost/127.0.0.1")
    root = Path(workspace_root).resolve()
    web = Path(web_root).resolve()
    return LocalJobAgentServer((host, port), LocalJobAgentHandler, root, web)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the local job-agent web UI and API")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--web-root", default="web")
    args = parser.parse_args(argv)
    server = build_server(host=args.host, port=args.port, workspace_root=args.workspace, web_root=args.web_root)
    print(f"Serving job-agent UI: http://{args.host}:{args.port}/web/index.html")
    print(f"Workspace root: {server.workspace_root}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
