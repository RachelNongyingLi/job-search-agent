# Agent Instructions

This repo is a local-first precision job-search agent. The goal is not to make a candidate look bigger. The goal is to make application judgment more evidence-based, private, and honest.

## Start Every Application Task This Way

- Read `README.md`.
- Read the target JD file.
- Read `profiles/sample_candidate.json` for public-safe demo behavior.
- If present and explicitly relevant, read local private files such as `profiles/*.local.json`, `data/private/*.local.json`, `memory.local.json`, and the latest private report under `outputs/private/`.
- Run `job-agent analyze` before CV tailoring when the user is judging a new role.
- Prefer `job-agent workflow run` for new roles because it writes the gate, next actions, CV plan, optional LLM verification, and memory artifacts together.
- Do not rely only on chat context or platform memory for application facts.

## Operating Modes

- Codex/Claude as operator: read these instructions, run the CLI, inspect `report.md`, `decision.json`, and `next_actions.md`, then help the user decide. You may add reasoning on top of CLI output, but you must not bypass the workflow gate.
- Local LLM drafting: use `job-agent workflow run --llm-provider ...` only when the user explicitly wants model-assisted drafting. LLM output is optional wording help, not a source of truth.
- In both modes, the deterministic matcher, negative ability check, memory discipline, CV/public-output confirmation, verifier, privacy rules, and one-page CV contract remain mandatory.
- Missing `cv_plan.md` is often intentional gate output, not a generation failure. Do not write substitute CV bullets when the gate withheld the plan.
- You may be more conservative than the CLI. You must not be less conservative than the CLI.

## Privacy Rules

- Never commit, stage, or publish private job-search material: real CVs, cover letters, `applications.csv`, `memory.local.json`, `*.local.json`, PDFs, DOCX files, transcripts, certificates, screenshots, or private reports.
- Treat legal name, email, phone, address, visa/work authorization, commute, relocation, student ID, school proof, transcripts, certificates, recruiter conversations, and application history as private by default.
- Public files may contain only anonymized, sample, or user-approved public-safe facts.
- Do not copy private facts from chat or local files into `README.md`, tests, sample profiles, examples, or public CV artifacts.
- Before any commit or final publication step, run `git status --short` and inspect any JSON, CSV, PDF, DOCX, TeX, Markdown report, or profile file that would be included.

## Web Frontend Rules

- `web/index.html` is a static local console. It may generate commands, Codex prompts, and artifact previews; it must not claim to execute the Python workflow by itself.
- Do not add analytics, remote fonts, remote scripts, cloud upload, API key storage, or localStorage persistence for private job-search data.
- Website/PDF/TXT JD input must converge to a local `.txt` or `.md` JD path before workflow analysis.
- A future local server must bind to localhost, use allowlisted private directories, call `run_workflow`, and keep CV/public-output confirmation at the UI boundary.
- The frontend must preserve the same gate semantics as the CLI: red-line blocks prevent CV planning and LLM drafting.

## Judgment Rules

- Check market hard filters before CV tailoring: language, location, onsite, commute, relocation, work authorization, mandatory internship proof, start date, and student status.
- Treat hard filters and repeated red lines as memory signals that can be learned across applications.
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

## LLM Integration Rules

- The default workflow should run with `--llm-provider none`.
- Do not call a local or remote LLM before the gate allows CV planning.
- A block-level red line forbids deterministic CV planning and optional LLM drafting, even when `--yes` is passed.
- A local LLM draft is acceptable only when `llm_verification.json` has `"passed": true`.
- If the verifier rejects the draft, use `cv_plan.md` and explain why the LLM draft was not accepted.
- Never let LLM output add unsupported eligibility, commute, relocation, language, production, leadership, deployment, metrics, or work-authorization claims.

## CV Tailoring Rules

- LaTeX CV work is the final step after `report.md`, `decision.json`, and an allowed `cv_plan.md`; do not start by editing `.tex` directly for a new role.
- Human confirmation is required at the CV/public-output boundary: editing CV bullets, turning private facts into public wording, sending messages, or accepting the final PDF.
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
- Memory can remember that proof, commute, relocation, language, or authorization is confirmed, unverified, blocked, or private; it is not by itself permission to publish that fact in CV text.
- Do not ask for human confirmation just to remember a recurring risk. Ask when the workflow would edit CV content, publish private facts, send application text, or mark a final one-page PDF as ready.
- Platform memory is optional recall. Required project behavior belongs in `AGENTS.md`, `CLAUDE.md`, README, tests, or code.

## Verification Commands

- Run tests with `PYTHONPATH=src python3 -m unittest discover -s tests`.
- Compile-check Python with `python3 -m compileall src tests`.
- For a sample workflow, run `PYTHONPATH=src python3 -m job_agent.cli workflow run --job examples/ai_automation_jd.txt --out-dir outputs/private/sample_workflow --yes`.
