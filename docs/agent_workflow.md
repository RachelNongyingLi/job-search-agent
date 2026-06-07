# Agent Workflow Notes

This file keeps the detailed Codex / Claude / CV workflow out of the README.

## Current Workflow Agents

The CLI exposes a human-in-the-loop workflow:

```bash
job-agent workflow run \
  --job inputs/jobs/company_role_YYYY-MM-DD.txt \
  --profile profiles/me.local.json \
  --out-dir outputs/private/company_role \
  --memory memory.local.json
```

Internally, the workflow is split into small agents:

- `IntakeAgent`: reads the JD and profile.
- `DecisionGateAgent`: runs matching, market filters, and negative red-line checks.
- `ReportAgent`: writes `report.md` and `decision.json`.
- `CVPlanAgent`: writes `cv_plan.md` only when the gate allows it.
- `LLMDraftAgent`: optionally asks a local/OpenAI-compatible LLM for wording help after CV planning is allowed, then verifies the draft before accepting it.
- `MemoryAgent`: updates `memory.local.json` when a memory path is provided.
- `NextActionsAgent`: writes `next_actions.md`.

The public entry point remains `run_workflow()`. It currently supports two engines:

- `classic`: the default linear orchestrator with no optional dependencies.
- `langgraph`: an optional graph orchestrator that preserves the same gate logic, artifacts, and privacy boundaries.

The workflow uses memory to learn recurring filters, risks, and evidence patterns across applications. Human confirmation is reserved for CV/public-output boundaries such as generating a CV plan, drafting application text, or accepting a final one-page PDF. A red-line block stops CV planning even if `--yes` is passed.

For demos or CI:

```bash
job-agent workflow run \
  --job examples/ai_automation_jd.txt \
  --out-dir outputs/private/example_ai_automation \
  --memory memory.local.json \
  --yes
```

## Two Operating Modes

### Local Web Console

The repo includes a multilingual console at `web/index.html`. It can run in two modes.

Backend mode:

```bash
PYTHONPATH=src python3 -m job_agent.server --host 127.0.0.1 --port 8765 --workspace .
```

Then open `http://127.0.0.1:8765/web/index.html`. In this mode the HTML can call localhost APIs to save JD text, run `run_workflow`, and render returned artifacts.

Static-only mode: open `web/index.html` directly or serve it with a generic static server. In this mode it can prepare commands, copy Codex prompts, scan/import local files when the browser allows it, and render artifacts, but it cannot execute Python.

It is organized into three user-facing views:

- **Application round**: JD evidence, fit-analysis artifacts, and CV-planning boundary
- **First use**: workspace setup, `memory.local.json` creation, initial CV baseline, and Codex operator tutorial
- **Settings**: fixed workspace paths, private file locations, and optional LLM API flags

Use it to:

- set a fixed local workspace root
- require an initial CV baseline before real CV tailoring
- scan the selected local workspace for expected files before asking for manual imports
- choose a JD source type: website URL, PDF reference, TXT/Markdown, or direct JD text
- prepare local paths for JD, profile, output, and memory
- run the workflow through the localhost backend, or generate `job-agent workflow run` commands as fallback
- configure optional LLM flags without storing API keys
- import `decision.json`, `report.md`, `next_actions.md`, `cv_plan.md`, and `llm_verification.json`
- copy a Codex operator prompt

Current boundary: static-only HTML cannot run the Python CLI, parse PDFs reliably, scrape websites, or build a final PDF CV. Backend mode can call the local Python workflow but still treats website URLs and PDFs as source references until Codex or a localhost extractor turns them into reviewed JD text. The workflow still runs from a local `.txt` or `.md` JD path.

The fixed workspace model is:

```text
inputs/jobs/<application>.txt      # reviewed JD text
private_resumes/base_cv.pdf        # initial private CV baseline
profiles/me.local.json             # private structured profile
memory.local.json                  # private cross-application memory
outputs/private/<application>/     # workflow artifacts
```

The initial CV baseline is required for real CV work because it lets Codex or a future local server understand existing evidence before changing role-specific wording. It is private evidence, not public output, and it does not bypass claim-evidence checks.

The frontend should follow this lookup order:

1. User chooses the workspace folder in the browser.
2. The UI checks the expected fixed paths.
3. Found artifacts are rendered directly in the interface.
4. Missing artifacts are marked red.
5. Manual import controls remain available as fallback.

Backend boundary: `job_agent.server` wraps `run_workflow` behind localhost APIs. It must keep paths inside the selected workspace, avoid remote upload by default, and preserve explicit CV/public-output confirmation.

Backend API shape:

- `GET /api/health` returns backend status and the resolved workspace root.
- `POST /api/workspace/create` creates private folders, `memory.local.json`, a starter profile, and the output folder. Use `job_path`, `profile_path`, `cv_path` or `initial_cv_path`, `out_dir`, and `memory_path`.
- `POST /api/files/base-cv` saves the uploaded baseline CV under `private_resumes/`. Use `cv_path`; `path` is accepted as an alias for operator ergonomics.
- `POST /api/jobs/text` saves reviewed JD text under `inputs/jobs/`. Use `job_path` and `content`; `path` and `text` are accepted as aliases.
- `POST /api/workflows/run` calls `run_workflow` with `job_path`, `profile_path`, `out_dir`, `memory_path`, company/title overrides, strict boolean `auto_approve`, optional `engine` (`classic` or `langgraph`), and optional local LLM flags.
- `GET /api/artifacts?out_dir=outputs/private/<slug>` reloads existing workflow artifacts.

The server rejects workspace escapes, non-private output paths, remote LLM base URLs in local backend mode, and string booleans such as `"true"` for `auto_approve`.

## Optional LangGraph Orchestration

LangGraph is useful once the workflow needs explicit state, conditional edges, durable resume, and human-in-the-loop interruption. The project should not use it as a new source of truth for scoring. The deterministic matcher and negative-ability gate remain authoritative.

Install it only when needed:

```bash
pip install -e ".[langgraph]"
```

Run the same workflow with a different orchestrator:

```bash
job-agent workflow run \
  --job inputs/jobs/company_role_YYYY-MM-DD.txt \
  --profile profiles/me.local.json \
  --out-dir outputs/private/company_role \
  --memory memory.local.json \
  --engine langgraph
```

Current graph shape:

```text
intake
  -> gate
  -> report
  -> cv_plan       # skipped on red_line_block
  -> llm_draft     # only if cv_plan exists and LLM is enabled
  -> memory
  -> next_actions
```

Rules that must stay true in both engines:

- `red_line_block` writes report, decision, memory when enabled, and next actions; it must not write `cv_plan.md` or `cv_plan.llm.md`.
- `needs_verification` does not produce a CV plan unless the same confirmation policy allows it.
- LLM drafting runs only after deterministic CV planning exists.
- `decision.json`, `report.md`, `next_actions.md`, optional `cv_plan.md`, optional `cv_plan.llm.md`, and optional `llm_verification.json` keep the same names and meanings.
- LangGraph state and future checkpoints must stay local and private; do not send full profile, CV, JD, memory, or checkpoints to remote tracing by default.

Future durable-checkpoint mode should add a separate start/resume API instead of weakening the current run API:

- `POST /api/workflows/start`: create a local graph run and stop at the first CV/public-output checkpoint.
- `GET /api/workflows/<id>`: inspect gate, pending checkpoint, and artifacts.
- `POST /api/workflows/<id>/resume`: continue only after explicit user approval.

Until that API exists, the LangGraph engine is an optional orchestrator, not a different product mode.

### Mode 1: Codex Or Claude As Operator

This is the current recommended mode.

- Codex reads `AGENTS.md`.
- Claude Code reads `CLAUDE.md`, which imports `AGENTS.md`.
- The operator runs `job-agent workflow run`, reads the artifacts, and reasons with the user.
- The operator can compare roles, explain tradeoffs, and plan CV edits after the gate allows it.
- The operator must not raise scores, ignore red lines, or convert missing evidence into CV claims.

This mode does not require the project code to call an LLM. The LLM is the operator around the CLI.

#### Operator Contract

Required sequence:

1. Read `README.md` and `AGENTS.md` or `CLAUDE.md`.
2. Read the JD, selected profile, and relevant local memory.
3. Run `job-agent workflow run`.
4. Read `decision.json`, `report.md`, and `next_actions.md`.
5. Produce CV or cover-letter planning only if the workflow status allows it.

The operator may be more conservative than the CLI. It must not be less conservative than the CLI. A missing `cv_plan.md` should be treated as an intentional gate result unless the command failed.

### Mode 2: Local LLM Drafting

This mode is for a local app, local server, or scripted deployment that wants model-assisted wording.

```bash
job-agent workflow run \
  --job inputs/jobs/company_role_YYYY-MM-DD.txt \
  --profile profiles/me.local.json \
  --out-dir outputs/private/company_role \
  --llm-provider openai-compatible \
  --llm-base-url http://localhost:11434/v1 \
  --llm-model your-local-model \
  --yes
```

The local LLM layer is deliberately late in the pipeline:

```text
JD + profile
  -> deterministic matcher
  -> market and negative ability gate
  -> memory signal update when --memory is provided
  -> CV/public-output confirmation
  -> deterministic cv_plan.md
  -> optional LLM draft
  -> verifier
  -> cv_plan.llm.md only if accepted
```

The LLM receives a compact analysis summary, not the full private profile by default. It can suggest wording, but `llm_verification.json` must pass before `cv_plan.llm.md` is treated as usable.

For test and demos without network:

```bash
job-agent workflow run \
  --job examples/ai_automation_jd.txt \
  --out-dir outputs/private/mock_llm_demo \
  --llm-provider mock \
  --yes
```

## Why This Is Still An Agent

The project is an agentic workflow because it has specialized agents, persistent memory, explicit gates, generated artifacts, and human confirmation at CV/public-output boundaries. It is not yet an autonomous auto-apply bot, and it should not become one by default.

The key design choice is separation:

- Deterministic agents decide fit, risks, and claim safety.
- Codex/Claude operator mode adds human-facing reasoning around files and CLI output.
- Local LLM mode adds optional wording help after the gate.
- The verifier decides whether an LLM draft is acceptable.

Required project behavior belongs in checked-in instruction files, code, and tests, not only in platform memory. Local private facts belong in ignored files such as `profiles/me.local.json`, `data/private/*.local.json`, and `memory.local.json`.

## Memory Signals Vs Human Checkpoints

Memory should learn across rounds:

- whether hard filters tend to appear for certain roles
- whether mandatory internship proof, commute, relocation, language, or authorization is confirmed, unverified, blocked, or private
- recurring root strengths, upskill gaps, red lines, and do-not-claim items

Human confirmation is needed when the workflow would change public-facing application material:

- editing CV bullets or LaTeX
- turning a private fact into public wording
- sending a CV, cover letter, or recruiter message
- accepting the final one-page PDF as ready

Memory may remind the agent that something is confirmed or blocked. It still cannot publish private facts or invent evidence.

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
job-agent workflow run \
  --job inputs/jobs/company_role_YYYY-MM-DD.txt \
  --profile profiles/me.local.json \
  --out-dir outputs/private/company_role \
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
Read outputs/private/company_role/report.md and my current CV.
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
