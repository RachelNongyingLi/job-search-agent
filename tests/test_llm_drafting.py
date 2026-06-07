import unittest

from job_agent.llm_drafting import verify_llm_cv_plan
from job_agent.models import JobAnalysis, MatchResult


def _result() -> MatchResult:
    return MatchResult(
        score=82,
        decision="apply",
        matched=[],
        gaps=[],
        root_matches=["Python", "LLM"],
        upskill_matches=["Kubernetes"],
        irrelevant_or_low_signal=[],
        market_risks=[],
        memory_updates=[],
        job=JobAnalysis(
            title="AI Automation Intern",
            company="Example Co",
            keywords=[],
            responsibilities=[],
            requirements=[],
            raw_text="",
        ),
    )


class LLMDraftingTest(unittest.TestCase):
    def test_verifier_accepts_cautious_evidence_disciplined_plan(self):
        verification = verify_llm_cv_plan(
            """
            ## Safe Emphasis
            Use evidence from the local report.

            ## Do Not Claim
            Do not invent deployment, leadership, metrics, or eligibility proof.
            """,
            _result(),
        )

        self.assertTrue(verification.passed)

    def test_verifier_rejects_unsupported_positive_claims(self):
        verification = verify_llm_cv_plan(
            """
            ## Safe Emphasis
            Use evidence from the local report.
            The candidate deployed to production, led a team, and has deep experience in Kubernetes.

            ## Do Not Claim
            Keep claims truthful.
            """,
            _result(),
        )

        self.assertFalse(verification.passed)
        self.assertGreaterEqual(len(verification.warnings), 2)


if __name__ == "__main__":
    unittest.main()
