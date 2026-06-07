import json
import tempfile
import unittest
from pathlib import Path

from job_agent.job_parser import analyze_job_text
from job_agent.matcher import match_profile_to_job
from job_agent.memory import update_memory
from job_agent.models import CandidateProfile


class MemoryTest(unittest.TestCase):
    def test_memory_stores_negative_signals_separately(self):
        profile = CandidateProfile(
            name="Test Candidate",
            headline="AI automation student",
            target_roles=["AI Automation Intern"],
            locations=["Germany"],
            education=[],
            skills={"ai": ["Python", "LLM", "Agent", "Automation"]},
            experiences=[],
            projects=[],
            languages=["English"],
            ability_model={"root_strengths": ["Python", "LLM", "Agent", "Automation"]},
        )
        job = analyze_job_text(
            "AI automation intern. Proof of mandatory internship is required. Work with Python and LLM agents.",
            company="Example",
            title="AI Automation Intern",
        )
        result = match_profile_to_job(profile, job)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "memory.local.json"
            update_memory(path, result)
            memory = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(memory["applications"][0]["negative_signals"][0]["code"], "mandatory_internship_unverified")
        self.assertEqual(memory["summary"]["top_negative_signals"][0][0], "mandatory_internship_unverified")


if __name__ == "__main__":
    unittest.main()
