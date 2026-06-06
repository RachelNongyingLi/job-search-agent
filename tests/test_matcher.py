import unittest

from job_agent.job_parser import analyze_job_text
from job_agent.matcher import match_profile_to_job
from job_agent.models import CandidateProfile


class MatcherTest(unittest.TestCase):
    def test_ai_automation_role_scores_as_strong_match(self):
        profile = CandidateProfile(
            name="Test Candidate",
            headline="AI automation student",
            target_roles=["AI Automation Intern", "Machine Learning Intern"],
            locations=["Germany"],
            education=[],
            skills={
                "ai": ["Python", "LLM", "Agent", "Prompt Engineering", "Machine Learning", "Documentation", "Excel"],
                "business": ["Automation", "Workflow", "International Collaboration"],
            },
            experiences=[],
            projects=[
                {
                    "title": "LLM Agent Workflow",
                    "keywords": ["LLM", "Agent", "Python Workflow", "Model Evaluation"],
                    "bullets": ["Built a Python workflow for prompt construction and result parsing."],
                }
            ],
            languages=["English"],
        )
        job = analyze_job_text(
            "Build Python workflow automation with LLM agents, prompt engineering, documentation, Excel, and international stakeholders.",
            company="Example",
            title="AI Automation Intern",
        )

        result = match_profile_to_job(profile, job)

        self.assertGreaterEqual(result.score, 75)
        self.assertTrue(any(keyword == "llm" for keyword, _ in result.matched))
        self.assertIn("Strong apply", result.decision)

    def test_market_hard_filter_flags_unclaimed_german(self):
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
            market_facts={
                "languages_claimed": ["English"],
                "languages_not_claimed": ["German"],
                "work_authorization": "Keep private.",
            },
            ability_model={"root_strengths": ["Python", "LLM", "Agent", "Automation"]},
        )
        job = analyze_job_text(
            "AI automation intern. German B1 required. Work with Python and LLM agents.",
            company="Example",
            title="AI Automation Intern",
        )

        result = match_profile_to_job(profile, job)

        self.assertTrue(any("German" in risk for risk in result.market_risks))
        self.assertIn("verify", result.decision.lower())


if __name__ == "__main__":
    unittest.main()
