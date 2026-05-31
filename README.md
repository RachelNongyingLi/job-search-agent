# Personal Job Search Agent

A local-first CLI assistant for job matching, resume targeting, application materials, and application tracking.

This project was built around a Quantitative Data Science profile with strengths in LLM/agent workflows, NLP, machine learning evaluation, causal inference, psychometrics, and Python automation. It is designed to be safe to publish on GitHub: private resumes, transcripts, phone numbers, and application records are ignored by default.

## What It Does

- Analyzes a job description from a local `.txt` or `.md` file.
- Matches the role against a structured candidate profile.
- Produces a Markdown report with fit score, strong evidence, gaps, resume targeting advice, cover letter draft, recruiter message, and interview prep prompts.
- Tracks applications in a simple CSV file.
- Runs without external APIs or network access.

## Quick Start

```bash
cd job-search-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
job-agent analyze --job examples/ai_automation_jd.txt --out outputs/example_report.md
```

To print the report directly:

```bash
job-agent analyze --job examples/ai_automation_jd.txt
```

Track an application:

```bash
job-agent track add \
  --company "Example Semiconductor" \
  --role "AI Automation Intern" \
  --status "tailoring" \
  --resume-version "Nongying_Li_AI_Automation_2026-05.pdf"

job-agent track list
```

## Example Output

The report includes sections like:

```text
Fit score: 90/100
Decision: Strong apply: tailor the resume and apply.

Strong Evidence To Emphasize
- llm: skill:ai_ml, Agentic AI Research: CALE Framework for LLM Reasoning and Evaluation
- automation: skill:business
- python: skill:programming

Resume Targeting Plan
- Lead with the CALE agentic AI project.
- Keep the NLP information extraction project visible.
- Add one collaboration bullet for mixed technical/non-technical stakeholders.
```

## Candidate Profile

The public profile lives at:

```text
profiles/nongying_public.json
```

It contains a GitHub-safe version of the resume background:

- University of Tübingen M.Sc. Quantitative Data Science.
- Hong Kong Baptist University B.Sc. Data Science with Honours.
- CALE agentic AI workflow for LLM reasoning and evaluation.
- NLP joint entity and relation extraction.
- Research assistant work in causal inference.
- Mask-aware VAE imputation and IRT evaluation.
- Python, PyTorch, Transformers, Pandas, Scikit-learn, SQL, R, C++, Java.

Private contact details, date of birth, student ID, transcripts, and original documents are intentionally not included.

## Project Structure

```text
job-search-agent/
├── docs/
│   └── analysis_zh.md
├── examples/
│   └── ai_automation_jd.txt
├── profiles/
│   └── nongying_public.json
├── src/job_agent/
│   ├── cli.py
│   ├── generator.py
│   ├── job_parser.py
│   ├── matcher.py
│   ├── models.py
│   ├── profile.py
│   └── tracker.py
├── tests/
│   └── test_matcher.py
├── .gitignore
├── pyproject.toml
└── README.md
```

## Privacy Model

This repository is public-safe by default.

Ignored by `.gitignore`:

```text
data/private/
outputs/private/
outputs/
applications.csv
*.docx
*.pdf
*.xlsx
*.xls
```

Keep original resumes, enrollment verification, transcripts, and application records in ignored private folders. The agent can still use public examples and the sanitized profile for demos.

## Workflow

1. Save a JD as a text file.
2. Run `job-agent analyze`.
3. Read the generated Markdown report.
4. Update the resume manually using the targeting plan.
5. Track the application with `job-agent track add`.
6. Prepare interviews using the generated prompts.

See [docs/analysis_zh.md](docs/analysis_zh.md) for the Chinese needs analysis, resume positioning, workflow design, MVP boundary, and roadmap.

## Roadmap

- Add a private profile mode for local-only contact details and work authorization notes.
- Add `.docx` resume generation from selected profile sections.
- Add STAR story bank and interview-prep commands.
- Add optional LLM provider support for richer JD parsing and writing style.
- Add a small local dashboard for pipeline review.

## Disclaimer

The agent is an assistant, not an auto-apply bot. It should not invent experience, submit applications without review, or expose private documents in a public repository.
