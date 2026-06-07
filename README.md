# Apply Less, Fit More

A local-first job-search assistant for deciding whether a role is worth tailoring.

It does **not** auto-apply. It does **not** invent experience. It helps you answer:

- Is this role a real fit?
- Is there a hard blocker, such as language, location, work authorization, commute, or mandatory internship proof?
- Which strengths are evidence-backed?
- Which gaps are learnable before interview?
- What should not be claimed on the CV?

## What It Does

- Reads a local job description.
- Matches it against a structured candidate profile.
- Produces a Markdown report with:
  - fit score
  - apply / verify-first / skip decision
  - market hard filters
  - red-line risks
  - root strengths
  - interview-upskill items
  - do-not-claim items
  - resume targeting advice
- Optionally updates a private local memory file.
- Tracks applications in a local CSV.

## Quick Start

```bash
cd job-search-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run the human-in-the-loop workflow:

```bash
job-agent workflow run \
  --job examples/ai_automation_jd.txt \
  --out-dir outputs/private/example_ai_automation \
  --memory memory.local.json
```

The workflow writes:

```text
report.md        # full match report
decision.json    # machine-readable decision
next_actions.md  # what to do next
cv_plan.md       # only when the gate allows CV planning
```

For scripting or demos, approve non-blocking prompts:

```bash
job-agent workflow run \
  --job examples/ai_automation_jd.txt \
  --out-dir outputs/private/example_ai_automation \
  --memory memory.local.json \
  --yes
```

Use the lower-level analyzer when you only want a report:

```bash
job-agent analyze \
  --job examples/ai_automation_jd.txt \
  --out outputs/example_report.md
```

Analyze and update local memory:

```bash
job-agent analyze \
  --job examples/ai_automation_jd.txt \
  --out outputs/example_report.md \
  --memory memory.local.json
```

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Use Your Own Profile

The public sample profile is anonymized:

```text
profiles/sample_candidate.json
```

For real use, create a local private copy:

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

Keep real job descriptions in `inputs/jobs/` and real reports in `outputs/private/`.

## Track Applications

```bash
job-agent track add \
  --company "Example Company" \
  --role "AI Automation Intern" \
  --status "tailoring" \
  --notes "Verify location before CV tailoring"

job-agent track list
```

## Codex Or Claude

This repo includes agent instructions:

```text
AGENTS.md      # Codex instructions
CLAUDE.md      # Claude Code instructions
```

Use Codex or Claude to review reports, plan CV edits, or compare multiple roles. The important rule:

```text
Run the workflow first. Do not tailor the CV until hard filters and red lines are checked.
```

Advanced prompts and the planned one-page LaTeX CV workflow are in [docs/agent_workflow.md](docs/agent_workflow.md).

## Privacy

Do not commit private job-search material:

- real CVs
- cover letters
- `memory.local.json`
- `applications.csv`
- `*.local.json`
- PDFs / DOCX files
- transcripts or certificates
- visa, address, commute, or work-authorization details

Ignored by default:

```text
data/private/
inputs/jobs/
private_resumes/
outputs/private/
outputs/
applications.csv
memory.local.json
*.local.json
CLAUDE.local.md
*.docx
*.pdf
*.xlsx
*.xls
```

Rule of thumb: if you would not paste it into a public GitHub issue, do not put it in a tracked file.

## Project Structure

```text
job-search-agent/
├── AGENTS.md
├── CLAUDE.md
├── docs/
│   ├── agent_workflow.md
│   └── analysis_zh.md
├── examples/
│   └── ai_automation_jd.txt
├── profiles/
│   └── sample_candidate.json
├── src/job_agent/
│   ├── cli.py
│   ├── generator.py
│   ├── job_parser.py
│   ├── matcher.py
│   ├── memory.py
│   ├── models.py
│   ├── negative_ability.py
│   ├── profile.py
│   └── tracker.py
└── tests/
    ├── test_generator.py
    ├── test_matcher.py
    └── test_memory.py
```

## Status

MVP. Useful for local triage and truthful application planning. Not a replacement for judgment.
