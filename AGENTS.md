# Agent Instructions

This repo is a local-first precision job-search agent. The goal is not to make a candidate look bigger. The goal is to make application judgment more evidence-based, private, and honest.

## Start Every Application Task This Way

- Read `README.md`.
- Read the target JD file.
- Read `profiles/sample_candidate.json` for public-safe demo behavior.
- If present and explicitly relevant, read local private files such as `profiles/*.local.json`, `data/private/*.local.json`, `memory.local.json`, and the latest private report under `outputs/private/`.
- Run `job-agent analyze` before CV tailoring when the user is judging a new role.
- Do not rely only on chat context or platform memory for application facts.

## Privacy Rules

- Never commit, stage, or publish private job-search material: real CVs, cover letters, `applications.csv`, `memory.local.json`, `*.local.json`, PDFs, DOCX files, transcripts, certificates, screenshots, or private reports.
- Treat legal name, email, phone, address, visa/work authorization, commute, relocation, student ID, school proof, transcripts, certificates, recruiter conversations, and application history as private by default.
- Public files may contain only anonymized, sample, or user-approved public-safe facts.
- Do not copy private facts from chat or local files into `README.md`, tests, sample profiles, examples, or public CV artifacts.
- Before any commit or final publication step, run `git status --short` and inspect any JSON, CSV, PDF, DOCX, TeX, Markdown report, or profile file that would be included.

## Judgment Rules

- Check market hard filters before CV tailoring: language, location, onsite, commute, relocation, work authorization, mandatory internship proof, start date, and student status.
- Run or preserve the negative ability / red-line check before recommending deep tailoring.
- If a fact is private, unknown, unverified, or marked "ask locally", do not convert it into a positive resume claim.
- Negative memory must never be reinterpreted as strength.
- Use `verify first` or `skip` when a hard constraint is unresolved, even if technical keywords match.

## Anti-Hallucination Rules

- Do not convert "learnable" into "experienced".
- Do not convert "project exposure" into "production ownership".
- Do not convert coursework or research exploration into professional experience.
- Do not invent metrics, company names, deployment, leadership, users, revenue impact, certifications, language proficiency, authorization status, or eligibility proof.
- If evidence is missing, mark it as `interview-upskill`, `verify-first`, `unsupported`, or `do-not-claim`.

## CV Tailoring Rules

- For LaTeX CV work, preserve a one-page contract: the final PDF must be exactly one page.
- Prefer reordering, shortening, and evidence-first wording over adding new claims.
- Every proposed bullet should be labeled `safe`, `needs verification`, or `too strong / do not use`.
- Provide a claim-evidence table before final wording when changing CV content.
- If the CV exceeds one page, remove the weakest and least relevant content first. Do not shrink typography into an ugly or unreadable layout.
- If a beautiful one-page PDF cannot be produced, fail with a clear explanation instead of accepting a bad CV.

## Memory Rules

- Use `memory.local.json` as local application memory.
- Read it before analysis when present.
- Update it through `job-agent analyze --memory memory.local.json` unless the user explicitly asks for manual editing.
- Memory should preserve repeated root strengths, upskill gaps, market blockers, negative signals, and red lines.
- Platform memory is optional recall. Required project behavior belongs in `AGENTS.md`, `CLAUDE.md`, README, tests, or code.

## Verification Commands

- Run tests with `PYTHONPATH=src python3 -m unittest discover -s tests`.
- Compile-check Python with `python3 -m compileall src tests`.
- For a sample report, run `PYTHONPATH=src python3 -m job_agent.cli analyze --job examples/ai_automation_jd.txt`.
