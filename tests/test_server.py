from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from job_agent.server import ApiError, _create_workspace, _run_workflow_api, _safe_job_path, _safe_path, _write_base_cv


class ServerApiTests(unittest.TestCase):
    def test_safe_path_rejects_workspace_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ApiError):
                _safe_path(root, "../outside.txt")

    def test_job_path_must_stay_under_inputs_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ApiError):
                _safe_job_path(root, "README.md")
            with self.assertRaises(ApiError):
                _safe_job_path(root, "inputs/jobs/demo.pdf")
            self.assertEqual(_safe_job_path(root, "inputs/jobs/demo.txt"), (root / "inputs/jobs/demo.txt").resolve())

    def test_run_workflow_api_rejects_string_auto_approve(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "inputs/jobs").mkdir(parents=True)
            (root / "profiles").mkdir(parents=True)
            (root / "inputs/jobs/demo.txt").write_text("AI Automation Intern\nPython workflow", encoding="utf-8")
            (root / "profiles/me.local.json").write_text(_profile_json(), encoding="utf-8")

            with self.assertRaises(ApiError):
                _run_workflow_api(
                    root,
                    {
                        "job_path": "inputs/jobs/demo.txt",
                        "profile_path": "profiles/me.local.json",
                        "out_dir": "outputs/private/demo",
                        "auto_approve": "false",
                    },
                )

    def test_run_workflow_api_rejects_remote_llm_base_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "inputs/jobs").mkdir(parents=True)
            (root / "profiles").mkdir(parents=True)
            (root / "inputs/jobs/demo.txt").write_text("AI Automation Intern\nPython workflow", encoding="utf-8")
            (root / "profiles/me.local.json").write_text(_profile_json(), encoding="utf-8")

            with self.assertRaises(ApiError):
                _run_workflow_api(
                    root,
                    {
                        "job_path": "inputs/jobs/demo.txt",
                        "profile_path": "profiles/me.local.json",
                        "out_dir": "outputs/private/demo",
                        "auto_approve": True,
                        "llm_provider": "openai-compatible",
                        "llm_base_url": "https://api.example.com/v1",
                    },
                )

    def test_write_base_cv_requires_private_resumes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ApiError):
                _write_base_cv(root, {"cv_path": "profiles/base_cv.pdf", "content_base64": "ZGVtbw=="})
            result = _write_base_cv(root, {"cv_path": "private_resumes/base_cv.txt", "content_base64": "ZGVtbw=="})
            self.assertTrue(result["ok"])
            self.assertEqual((root / "private_resumes/base_cv.txt").read_text(encoding="utf-8"), "demo")

    def test_write_base_cv_accepts_path_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = _write_base_cv(root, {"path": "private_resumes/base_cv_alias.txt", "content_base64": "ZGVtbw=="})
            self.assertEqual(result["path"], "private_resumes/base_cv_alias.txt")
            self.assertEqual((root / "private_resumes/base_cv_alias.txt").read_text(encoding="utf-8"), "demo")

    def test_create_workspace_accepts_initial_cv_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = _create_workspace(
                root,
                {
                    "job_path": "inputs/jobs/demo.txt",
                    "profile_path": "profiles/me.local.json",
                    "initial_cv_path": "private_resumes/original_cv.pdf",
                    "out_dir": "outputs/private/demo",
                    "memory_path": "memory.local.json",
                },
            )
            self.assertEqual(result["created"]["cv_dir"], "private_resumes")
            self.assertTrue((root / "private_resumes").is_dir())

    def test_run_workflow_api_returns_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "inputs/jobs").mkdir(parents=True)
            (root / "profiles").mkdir(parents=True)
            (root / "inputs/jobs/demo.txt").write_text(
                "AI Automation Intern\nPython automation workflow documentation LLM prompt engineering.",
                encoding="utf-8",
            )
            (root / "profiles/me.local.json").write_text(_profile_json(), encoding="utf-8")

            payload = {
                "job_path": "inputs/jobs/demo.txt",
                "profile_path": "profiles/me.local.json",
                "out_dir": "outputs/private/demo",
                "auto_approve": True,
                "llm_provider": "none",
            }
            result = _run_workflow_api(root, payload)

            self.assertTrue(result["ok"])
            self.assertIn(result["status"], {"ready_for_cv_plan", "selective_cv_plan", "low_fit", "needs_verification"})
            self.assertIsInstance(result["artifacts"]["decision"], dict)
            self.assertIn("Job Match Report", result["artifacts"]["report"])
            self.assertIn("Next Actions", result["artifacts"]["next_actions"])
            self.assertTrue((root / "outputs/private/demo/decision.json").exists())


def _profile_json() -> str:
    return json.dumps(
        {
            "name": "Demo",
            "headline": "Private test profile",
            "target_roles": ["AI Automation Intern"],
            "locations": [],
            "education": [],
            "skills": {
                "programming": ["Python"],
                "ai_ml": ["LLM", "Prompt Engineering"],
                "business": ["Automation", "Workflow", "Documentation"],
            },
            "experiences": [],
            "projects": [
                {
                    "title": "Automation Workflow",
                    "keywords": ["Python", "Workflow", "LLM", "Prompt Engineering"],
                    "bullets": ["Built a local Python workflow for LLM prompt evaluation."],
                }
            ],
            "languages": [],
        }
    )


if __name__ == "__main__":
    unittest.main()
