# Apply Less, Fit More

A local-first job-search assistant for deciding whether a role is worth tailoring.

It does not auto-apply. It does not invent experience. It helps you find hard blockers, evidence-backed strengths, interview-upskill items, and things that must not be claimed on the CV.

## Quick Start

```bash
cd job-search-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run the main workflow:

```bash
job-agent workflow run \
  --job examples/ai_automation_jd.txt \
  --out-dir outputs/private/example_ai_automation \
  --memory memory.local.json
```

It writes:

```text
report.md            # human-readable fit report
decision.json        # machine-readable gate result
next_actions.md      # what to do next
cv_plan.md           # only when the gate allows CV planning
```

Use `--yes` only when you want to approve non-blocking prompts for demos or scripting.

## Local Web Console

You can also open the bilingual local console:

```text
web/index.html
```

It helps you prepare JD input, generate workflow commands, configure optional LLM flags, import `decision.json` / `report.md`, and copy a Codex prompt. It is static HTML: it does not upload data, store API keys, or directly run the Python CLI.

## Two Ways To Use It

### 1. Codex Or Claude As Operator

This is the recommended mode right now.

Open the repo in Codex or Claude Code and ask it to run the workflow. Codex reads `AGENTS.md`; Claude reads `CLAUDE.md`, which points back to the same rules.

Good prompt:

```text
Read AGENTS.md and README.md.
Run job-agent workflow for this JD.
Do not tailor my CV until the gate says it is allowed.
Use the report and decision.json for judgment.
```

Codex or Claude may reason over the CLI output, compare roles, and help plan CV edits. It must not bypass red lines, private evidence checks, or one-page CV rules.

### 2. Local LLM Drafting

By default, the CLI uses no language model. To add a local or self-hosted model, use an OpenAI-compatible endpoint after the deterministic gate:

```bash
job-agent workflow run \
  --job examples/ai_automation_jd.txt \
  --out-dir outputs/private/example_ai_automation \
  --llm-provider openai-compatible \
  --llm-base-url http://localhost:11434/v1 \
  --llm-model your-local-model \
  --yes
```

If accepted, the optional model draft is written to:

```text
cv_plan.llm.md
llm_verification.json
```

The model draft is wording help only. It cannot override red-line blocks, missing proof, unsupported claims, or verifier failures.

## Memory And Checkpoints

Across applications, memory should learn recurring signals:

- hard filters such as mandatory internship proof, commute, relocation, location, language, and work authorization
- repeated red lines, blocked roles, verify-first facts, and do-not-claim patterns
- evidence-backed strengths and recurring interview-upskill gaps

Human confirmation is needed when the workflow is about to change or send application material:

- editing CV bullets or LaTeX
- turning a private fact into public wording
- sending a CV, cover letter, or recruiter message
- accepting the final PDF as a clean, exactly one-page LaTeX CV

## Your Own Profile

The public profile is only a demo:

```text
profiles/sample_candidate.json
```

For real use:

```bash
cp profiles/sample_candidate.json profiles/me.local.json
```

Then run:

```bash
job-agent workflow run \
  --job inputs/jobs/company_role_YYYY-MM-DD.txt \
  --profile profiles/me.local.json \
  --out-dir outputs/private/company_role \
  --memory memory.local.json
```

## Privacy

Do not commit private job-search material: real CVs, cover letters, `memory.local.json`, `applications.csv`, `*.local.json`, PDFs, DOCX files, transcripts, certificates, visa details, address, commute, or work authorization.

Keep real job descriptions in `inputs/jobs/` and real outputs in `outputs/private/`.

## Useful Commands

```bash
job-agent analyze --job examples/ai_automation_jd.txt
job-agent track add --company "Example Company" --role "AI Automation Intern" --status "saved"
job-agent track list
PYTHONPATH=src python3 -m unittest discover -s tests
```

More detailed Codex/Claude, local LLM, and one-page LaTeX CV notes are in [docs/agent_workflow.md](docs/agent_workflow.md).
