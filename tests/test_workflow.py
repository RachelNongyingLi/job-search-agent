import json
import importlib.util
import tempfile
import unittest
from pathlib import Path

from job_agent.workflow import run_workflow


PROFILE_JSON = {
    "name": "Test Candidate",
    "headline": "AI automation student",
    "target_roles": ["AI Automation Intern", "Machine Learning Intern"],
    "locations": ["Sample City"],
    "education": [],
    "skills": {
        "ai": ["Python", "LLM", "Agent", "Prompt Engineering", "Machine Learning", "Documentation", "Excel"],
        "business": ["Automation", "Workflow", "International Collaboration"],
    },
    "experiences": [],
    "projects": [
        {
            "title": "LLM Agent Workflow",
            "keywords": ["LLM", "Agent", "Python Workflow", "Model Evaluation"],
            "bullets": ["Built a Python workflow for prompt construction and result parsing."],
        }
    ],
    "languages": ["English"],
    "ability_model": {"root_strengths": ["Python", "LLM", "Agent", "Prompt Engineering", "Machine Learning", "Documentation", "Workflow"]},
}


class WorkflowTest(unittest.TestCase):
    def test_workflow_generates_cv_plan_for_ready_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "profile.local.json"
            job = root / "job.txt"
            out_dir = root / "out"
            memory = root / "memory.local.json"
            profile.write_text(json.dumps(PROFILE_JSON), encoding="utf-8")
            job.write_text(
                "Build Python workflow automation with LLM agents, prompt engineering, documentation, Excel, and international stakeholders.",
                encoding="utf-8",
            )

            run = run_workflow(job, profile, out_dir=out_dir, memory_path=memory, auto_approve=True)

            self.assertEqual(run.status, "ready_for_cv_plan")
            self.assertTrue((out_dir / "report.md").exists())
            self.assertTrue((out_dir / "decision.json").exists())
            self.assertTrue((out_dir / "cv_plan.md").exists())
            self.assertTrue((out_dir / "next_actions.md").exists())
            self.assertTrue(memory.exists())

            decision = json.loads((out_dir / "decision.json").read_text(encoding="utf-8"))
            self.assertEqual(decision["agent_status"], "ready_for_cv_plan")
            self.assertIn("root_strengths", decision)

    def test_workflow_generates_verified_mock_llm_plan_after_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "profile.local.json"
            job = root / "job.txt"
            out_dir = root / "out"
            profile.write_text(json.dumps(PROFILE_JSON), encoding="utf-8")
            job.write_text(
                "Build Python workflow automation with LLM agents, prompt engineering, documentation, Excel, and international stakeholders.",
                encoding="utf-8",
            )

            run = run_workflow(
                job,
                profile,
                out_dir=out_dir,
                auto_approve=True,
                llm_provider="mock",
                llm_model="mock-local",
            )

            self.assertEqual(run.status, "ready_for_cv_plan")
            self.assertTrue((out_dir / "cv_plan.md").exists())
            self.assertTrue((out_dir / "cv_plan.llm.md").exists())
            self.assertTrue((out_dir / "llm_verification.json").exists())
            verification = json.loads((out_dir / "llm_verification.json").read_text(encoding="utf-8"))
            self.assertTrue(verification["passed"])
            self.assertEqual(verification["provider"], "mock")

    def test_workflow_keeps_deterministic_plan_when_llm_config_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "profile.local.json"
            job = root / "job.txt"
            out_dir = root / "out"
            profile.write_text(json.dumps(PROFILE_JSON), encoding="utf-8")
            job.write_text(
                "Build Python workflow automation with LLM agents, prompt engineering, documentation, Excel, and international stakeholders.",
                encoding="utf-8",
            )

            run = run_workflow(
                job,
                profile,
                out_dir=out_dir,
                auto_approve=True,
                llm_provider="openai-compatible",
            )

            self.assertEqual(run.status, "ready_for_cv_plan")
            self.assertTrue((out_dir / "cv_plan.md").exists())
            self.assertFalse((out_dir / "cv_plan.llm.md").exists())
            verification = json.loads((out_dir / "llm_verification.json").read_text(encoding="utf-8"))
            self.assertFalse(verification["passed"])
            self.assertEqual(verification["provider"], "openai-compatible")

    def test_workflow_blocks_cv_plan_for_red_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "profile.local.json"
            job = root / "job.txt"
            out_dir = root / "out"
            profile.write_text(json.dumps(PROFILE_JSON), encoding="utf-8")
            job.write_text(
                "AI automation intern. Proof of mandatory internship is required. Work with Python and LLM agents.",
                encoding="utf-8",
            )

            run = run_workflow(job, profile, out_dir=out_dir, auto_approve=True)

            self.assertEqual(run.status, "red_line_block")
            self.assertFalse((out_dir / "cv_plan.md").exists())
            self.assertIn("Stop Before Tailoring", (out_dir / "next_actions.md").read_text(encoding="utf-8"))

    def test_workflow_skips_llm_plan_for_red_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "profile.local.json"
            job = root / "job.txt"
            out_dir = root / "out"
            profile.write_text(json.dumps(PROFILE_JSON), encoding="utf-8")
            job.write_text(
                "AI automation intern. Proof of mandatory internship is required. Work with Python and LLM agents.",
                encoding="utf-8",
            )

            run = run_workflow(
                job,
                profile,
                out_dir=out_dir,
                auto_approve=True,
                llm_provider="mock",
            )

            self.assertEqual(run.status, "red_line_block")
            self.assertFalse((out_dir / "cv_plan.llm.md").exists())
            self.assertFalse((out_dir / "llm_verification.json").exists())

    def test_memory_update_is_opt_in_not_human_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "profile.local.json"
            job = root / "job.txt"
            out_dir = root / "out"
            memory = root / "memory.local.json"
            profile.write_text(json.dumps(PROFILE_JSON), encoding="utf-8")
            job.write_text(
                "AI automation intern. Proof of mandatory internship is required. Work with Python and LLM agents.",
                encoding="utf-8",
            )

            def fail_on_prompt(prompt):
                raise AssertionError(f"Unexpected human checkpoint: {prompt}")

            run = run_workflow(
                job,
                profile,
                out_dir=out_dir,
                memory_path=memory,
                input_fn=fail_on_prompt,
            )

            self.assertEqual(run.status, "red_line_block")
            self.assertTrue(memory.exists())
            self.assertFalse((out_dir / "cv_plan.md").exists())

    def test_unknown_workflow_engine_is_rejected(self):
        with self.assertRaises(ValueError):
            run_workflow("job.txt", "profile.json", engine="surprise")

    def test_langgraph_engine_reports_missing_optional_dependency(self):
        if importlib.util.find_spec("langgraph") is not None:
            self.skipTest("LangGraph is installed in this environment.")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(RuntimeError) as raised:
                run_workflow(root / "job.txt", root / "profile.json", out_dir=root / "out", engine="langgraph")
            self.assertIn("pip install -e '.[langgraph]'", str(raised.exception))

    def test_langgraph_engine_matches_classic_when_installed(self):
        if importlib.util.find_spec("langgraph") is None:
            self.skipTest("LangGraph optional dependency is not installed.")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = root / "profile.local.json"
            job = root / "job.txt"
            profile.write_text(json.dumps(PROFILE_JSON), encoding="utf-8")
            job.write_text(
                "Build Python workflow automation with LLM agents, prompt engineering, documentation, Excel, and international stakeholders.",
                encoding="utf-8",
            )

            classic = run_workflow(job, profile, out_dir=root / "classic", auto_approve=True)
            graph = run_workflow(job, profile, out_dir=root / "graph", auto_approve=True, engine="langgraph")

            self.assertEqual(graph.status, classic.status)
            self.assertEqual(graph.result.score, classic.result.score)
            self.assertTrue((root / "graph/decision.json").exists())
            self.assertTrue((root / "graph/next_actions.md").exists())


if __name__ == "__main__":
    unittest.main()
