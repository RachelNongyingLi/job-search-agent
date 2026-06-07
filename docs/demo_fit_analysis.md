# Demo Fit Analysis

This is a public-safe example of what the app is meant to show after a job description is loaded and the local backend finishes analysis.

It is not a real application result. It uses fictional role, company, profile, and CV evidence so the README can show the ideal output shape without exposing private files.

## Demo Input

- Company: Example Company
- Role: AI Automation Intern
- JD evidence: Python workflow automation, LLM evaluation, documentation, stakeholder communication
- Candidate evidence: demo profile with Python, LLM workflow, model evaluation, data preparation, and documentation projects
- Baseline CV: private placeholder, used only for understanding existing evidence

## Demo Result

```text
Fit score: 74/100
Gate: ready_for_cv_plan
Decision: Worth a careful application if no private market blocker appears.
```

## What The UI Should Make Obvious

- The role is not auto-approved just because keywords match.
- The score is paired with gate status, red-line checks, and do-not-claim items.
- CV planning is allowed only because the demo has no hard blocker.
- The plan should strengthen existing evidence, not invent new experience.

## Example Evidence Matches

- Python workflow automation
- LLM prompt and evaluation workflow
- Documentation and reproducible analysis
- Data preparation and structured reporting

## Example Verify-First Items

- Location, commute, and relocation must be checked privately.
- Work authorization must be confirmed privately before public wording.
- If the real JD requires mandatory internship proof, the workflow should block until proof exists.

## Example Do-Not-Claim Items

- Do not claim production ownership without evidence.
- Do not claim deployment metrics that are not in the profile, CV, project, or report.
- Do not claim language fluency, work authorization, or eligibility proof from memory alone.
- Do not rewrite a project into an unrelated domain just to match the JD.

## Example Next Action

If the user wants to continue, the safe next step is a CV plan that reorders and tightens existing evidence. The final LaTeX PDF still needs human approval and must compile to exactly one page.
