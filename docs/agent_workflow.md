# Agent Workflow Notes

This file keeps the detailed Codex / Claude / CV workflow out of the README.

## Codex And Claude

- Codex reads `AGENTS.md`.
- Claude Code reads `CLAUDE.md`, which imports `AGENTS.md`.
- Required project behavior belongs in checked-in instruction files, not only in platform memory.
- Local private facts belong in ignored files such as `profiles/me.local.json`, `data/private/*.local.json`, and `memory.local.json`.

## Suggested Prompt For A New Job

```text
You are my local job-search agent for this repo.

Before judging this role, read:
- README.md
- AGENTS.md or CLAUDE.md
- profiles/me.local.json if present
- memory.local.json if present
- the JD at inputs/jobs/<company_role_date>.txt

Do not tailor my CV yet.
First run or mirror the local analyzer and produce:
1. apply / selective apply / verify-first / skip decision
2. market hard filters
3. negative ability red lines
4. root strengths
5. interview-upskill items
6. do-not-claim items
7. what memory should remember
```

Run:

```bash
job-agent analyze \
  --job inputs/jobs/company_role_YYYY-MM-DD.txt \
  --profile profiles/me.local.json \
  --out outputs/private/company_role_report.md \
  --memory memory.local.json
```

## Multi-Round Applications

When comparing related roles, anchor the agent to files instead of chat history:

```text
Read memory.local.json and the latest report in outputs/private/.
Tell me whether this new role is genuinely better, worse, or just keyword-similar.

Do not raise the score because I want the role.
If old memory contains a red line, preserve it unless a private local fact explicitly resolves it.
```

## CV Tailoring

Use two steps.

First, ask for a plan:

```text
Read outputs/private/company_role_report.md and my current CV.
Create a CV targeting plan only.

Separate:
- supported claims I can safely emphasize
- claims that need weaker wording
- things that belong in interview prep, not the CV
- things I must not claim

Show a claim-evidence table before drafting bullets.
```

Then ask for edits:

```text
Now revise my CV bullets for this role.

Rules:
- Do not invent company names, production ownership, deployment, leadership, metrics, tools, authorization, or language fluency.
- Every strong claim must cite evidence from my profile, current CV, project, or report.
- If evidence is missing, write it as an upskill/interview-prep item instead.
- Preserve red-line warnings from memory.local.json and the report.
- Label every bullet as safe, needs verification, or too strong / do not use.
```

## Future LaTeX CV Contract

The planned CV workflow is a truth-preserving one-page LaTeX compiler.

```text
templates/cv.tex                  # public-safe one-page LaTeX template
profiles/sample_candidate.json    # anonymized demo profile
profiles/me.local.json            # real private profile, ignored by Git
outputs/private/                  # generated CVs and QA reports, ignored by Git
```

A future command may look like this:

```bash
job-agent cv build \
  --job inputs/jobs/company_role_YYYY-MM-DD.txt \
  --profile profiles/me.local.json \
  --template templates/cv.tex \
  --out outputs/private/company_role_cv.pdf
```

The CV builder should accept an output only after QA passes:

- LaTeX compiles successfully.
- The PDF is exactly one page.
- No private data leaks into public outputs.
- No unsupported claim appears.
- No red-line rule is violated.
- A `.qa.json` report is written next to the PDF.

If the CV does not fit on one page, remove the weakest and least relevant content first. If it still cannot fit cleanly, fail with a clear explanation.

## Safe Use Checklist

- Use `profiles/sample_candidate.json` for public demos only.
- Put your real profile in a `*.local.json` file.
- Treat `memory.local.json` as sensitive.
- Keep visa, address, phone, email, student ID, transcripts, certificates, commute details, and application history out of Git.
- Store real application outputs under `outputs/private/`.
- Never ask an agent to commit generated CVs, cover letters, application trackers, or private memory.
- Before publishing a CV or report, check that every claim is public-safe and evidence-backed.
- If a job requires work authorization, mandatory internship proof, relocation, onsite work, or local language fluency, verify privately before generating application text.
- Run `git status --short` before every commit and inspect any profile, report, CSV, PDF, DOCX, TeX, or JSON file that appears.

Rule of thumb: if you would not paste it into a public GitHub issue, do not put it in a tracked file.
