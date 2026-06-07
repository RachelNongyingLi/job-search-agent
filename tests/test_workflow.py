import json
import tempfile
import unittest
from pathlib import Path

from job_agent.workflow import run_workflow


PROFILE_JSON = {
    "name": "Test Candidate",
    "headline": "AI automation student",
    "target_roles": ["AI Automation Intern", "Machine Learning Intern"],
    "locations": ["Germany"],
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


if __name__ == "__main__":
    unittest.main()
