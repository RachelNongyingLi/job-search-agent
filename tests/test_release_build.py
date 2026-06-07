from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


def _load_release_module():
    root = Path(__file__).resolve().parents[1]
    module_path = root / "scripts/build_release.py"
    spec = importlib.util.spec_from_file_location("build_release", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load build_release.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


release = _load_release_module()


class ReleaseBuildTests(unittest.TestCase):
    def test_build_release_zip_excludes_private_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_repo(root)
            (root / "memory.local.json").write_text("{}", encoding="utf-8")
            (root / "private_resumes").mkdir()
            (root / "private_resumes/base_cv.pdf").write_bytes(b"private")
            (root / "outputs/private/demo").mkdir(parents=True)
            (root / "outputs/private/demo/report.md").write_text("private report", encoding="utf-8")

            build = release.build_release(root, root / "dist/releases", version="0.0.1")

            self.assertTrue(build.archive_path.exists())
            self.assertTrue(build.sha256_path.exists())
            with zipfile.ZipFile(build.archive_path, "r") as archive:
                names = archive.namelist()
            self.assertIn("apply-less-fit-more-v0.0.1/README.md", names)
            self.assertIn("apply-less-fit-more-v0.0.1/web/index.html", names)
            self.assertNotIn("apply-less-fit-more-v0.0.1/memory.local.json", names)
            self.assertFalse(any("private_resumes" in name for name in names))
            self.assertFalse(any("outputs/private" in name for name in names))

    def test_path_audit_rejects_private_release_names(self) -> None:
        cases = [
            "memory.local.json",
            "profiles/me.local.json",
            "private_resumes/base_cv.pdf",
            "outputs/private/demo/report.md",
            "applications.csv",
        ]
        for rel_path in cases:
            with self.subTest(rel_path=rel_path):
                self.assertTrue(release.audit_release_path(rel_path))

    def test_content_audit_rejects_secret_like_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "README.md"
            fake_key = "sk-" + "proj-" + "abcdefghijklmnopqrstuvwxyz123456"
            path.write_text("OPENAI_API_KEY=" + fake_key, encoding="utf-8")

            issues = release.audit_file_content(path, "README.md")

            self.assertTrue(issues)

    def test_dry_run_lists_release_files_without_writing_zip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_repo(root)

            build = release.build_release(root, root / "dist/releases", version="0.0.1", dry_run=True)

            self.assertIn("README.md", build.files)
            self.assertIn("web/index.html", build.files)
            self.assertFalse(build.archive_path.exists())


def _write_minimal_repo(root: Path) -> None:
    for path, content in {
        "README.md": "# Demo\n",
        "AGENTS.md": "# Agent rules\n",
        "CLAUDE.md": "# Claude rules\n",
        "pyproject.toml": '[project]\nversion = "0.0.1"\n',
        "docs/agent_workflow.md": "# Workflow\n",
        "examples/ai_automation_jd.txt": "AI Automation Intern\n",
        "profiles/sample_candidate.json": '{"name": "Demo Applicant"}\n',
        "src/job_agent/__init__.py": "\n",
        "tests/test_placeholder.py": "def test_placeholder():\n    assert True\n",
        "web/index.html": "<!doctype html><title>Demo</title>\n",
    }.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
