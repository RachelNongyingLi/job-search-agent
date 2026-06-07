import unittest

from job_agent.generator import build_report
from job_agent.job_parser import analyze_job_text
from job_agent.matcher import match_profile_to_job
from job_agent.models import CandidateProfile


class GeneratorTest(unittest.TestCase):
    def test_report_shows_red_lines_and_withholds_drafts(self):
        profile = CandidateProfile(
            name="Test Candidate",
            headline="AI automation student",
            target_roles=["AI Automation Intern"],
            locations=["Sample City"],
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

        report = build_report(profile, result)

        self.assertIn("Negative Ability / Red-Line Check", report)
        self.assertIn("mandatory or compulsory internship", report)
        self.assertIn("Draft withheld", report)


if __name__ == "__main__":
    unittest.main()
