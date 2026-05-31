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


if __name__ == "__main__":
    unittest.main()
