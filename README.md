# Apply Less, Fit More 🚀

> **A local-first job search agent that kills resume spam and turns applications into evidence.**
>
> **"（Even tho the funny thing is that we knew all these job-hunting tips come from either people who landed a job a decade ago, or people who haven't even found one yet. We literally have no good choices. :）"**

Everyone is using AI now.

- Companies use AI to screen candidates.
- Candidates use AI to blast out resumes.
- Recruiters drown in generated text.
- Applicants drown in silence.

So here is the uncomfortable truth:

**AI did not fix job search. It made low-quality applying cheaper.**

This project is built for the missing layer:

```text
Before writing a better resume,
ask whether this job is worth a better resume.
```

It is not an auto-apply bot.

It is a precision-application agent that tells you:

- what is a real fit
- what is a hard market blocker
- what can be learned before interview
- what should never be claimed
- what the next application should remember

No resume cosplay. No fake seniority. No “spray and pray” dashboard with nicer fonts.

Just better judgment, saved locally. 🧠

## The One-Picture Pitch

```mermaid
flowchart LR
    JD["Job Description"] --> Parser["JD Parser"]
    Profile["Anonymized Candidate Profile"] --> Matcher["Evidence Matcher"]
    Private["Private Local Facts<br/>language, location, work authorization"] --> Filters["Market Hard Filters"]
    Parser --> Filters
    Parser --> Matcher
    Matcher --> Triage["Ability Triage"]
    Filters --> Decision["Apply / Skip / Verify First"]
    Triage --> Decision
    Decision --> Report["Markdown Application Report"]
    Report --> Memory["Local Memory<br/>ignored by Git"]
    Memory --> Matcher

    classDef private fill:#fff4e6,stroke:#c76b00,color:#331b00;
    classDef output fill:#eef6ff,stroke:#2878bd,color:#102a43;
    class Private,Memory private;
    class Report,Decision output;
```

## The Resume Spam Era

Most AI job tools are built around the same funnel:

```text
resume + job description -> match score -> prettier resume -> more applications
```

Sounds great.

Until you realize the market does not only ask:

```text
Can this person do the work?
```

It also asks:

```text
Can we hire this person, here, now, under these constraints?
```

A candidate can be technically strong and still lose because of:

- language requirements
- work authorization
- onsite / hybrid expectations
- commute distance
- relocation constraints
- student status
- start date
- local hiring preference
- company-specific domain expectations

And then generic AI resume tools make it worse.

They do the one thing a serious candidate cannot afford:

> **They turn weak evidence into confident claims.**

They make you sound like you owned production systems you never touched, led teams you never led, or mastered tools you only saw in a tutorial. That may help with a keyword screen. It hurts the moment a human interviewer asks follow-up questions.

## The Bet

The next great job-search agent will not be the one that applies to 500 jobs while you sleep.

It will be the one brave enough to say:

```text
Do not spend three hours tailoring this.
The hard filter is language, not Python.
```

or:

```text
This is worth tailoring.
Your root evidence matches the role.
The only gap is learnable before interview.
```

or:

```text
Do not claim this.
Put it into the upskill plan instead.
```

That is the product.

Not more applications.

More correct applications.

## The Three Filters 🔥

### 1. Market Hard Filters: the stuff ATS tutorials ignore

Before talking about skills, the agent checks whether the job may be blocked by real-world constraints.

Examples:

- German required, but the profile does not claim German.
- Work authorization mentioned, but public profile keeps it private.
- Onsite / commute / relocation language appears in the JD.
- Local candidate preference may matter more than technical overlap.

This is where mass applying fails. It treats every job description like text. The real market treats some lines like gates.

### 2. Ability Triage: stop pretending every gap is the same

Every requirement is classified into one of three buckets.

| Bucket | Meaning | Resume Behavior |
|---|---|---|
| Root Strength | You can prove it with projects, research, coursework, or work. | Emphasize it. |
| Interview-Upskill | You can realistically learn or refresh it before interview. | Prepare it, do not overclaim it. |
| Low-Signal / Unsupported | It is irrelevant, too senior, noisy, or not backed by evidence. | Do not stuff it into the resume. |

This is the anti-hallucination layer.

The goal is not to make the candidate sound bigger. The goal is to make the candidate harder to misunderstand.

### 3. Local Application Memory: every rejection should teach the next application

One application should make the next one smarter.

The agent can update an ignored local memory file with:

- repeated market blockers
- repeated learnable gaps
- role clusters where root strengths show up
- signals that should affect future targeting

The memory is local. The public repo stays clean.

```bash
job-agent analyze \
  --job examples/ai_automation_jd.txt \
  --out outputs/example_report.md \
  --memory memory.local.json
```

## Under The Hood

```mermaid
flowchart TB
    subgraph Inputs
        A["JD text file"]
        B["sample_candidate.json<br/>public-safe profile"]
        C["memory.local.json<br/>private, ignored"]
    end

    subgraph Core
        D["job_parser.py<br/>extract role signals"]
        E["matcher.py<br/>score + classify"]
        F["generator.py<br/>write report"]
        G["memory.py<br/>learn across applications"]
        H["tracker.py<br/>CSV pipeline"]
    end

    subgraph Outputs
        I["Fit score"]
        J["Market hard filters"]
        K["Root / Upskill / Low-signal triage"]
        L["Resume targeting plan"]
        M["Cover letter + recruiter message"]
    end

    A --> D --> E
    B --> E
    C --> E
    E --> F
    E --> G
    F --> I
    F --> J
    F --> K
    F --> L
    F --> M
    H --> N["applications.csv<br/>private, ignored"]
```

## Why This Should Exist Now

Agent projects in 2025-2026 are converging on the same few truths:

- **Local-first execution**: private data should stay on the user machine.
- **Durable memory**: agents need continuity across sessions, not one-off prompts.
- **Auditable artifacts**: the agent should leave behind reports, decisions, and traces.
- **Workflow-specific agents**: generic chat is giving way to narrow agents with real constraints.

Job search needs all four.

Not another cover-letter generator.

A local workflow that remembers what the market keeps telling you.

The brutal version:

```text
If the agent cannot remember why the last 30 applications failed,
it is not a job-search agent.
It is a text box with ambition.
```

## What It Does Today ✨

- Reads a local `.txt` or `.md` job description.
- Matches it against an anonymized structured candidate profile.
- Produces a Markdown report with:
  - fit score
  - apply decision
  - evidence-backed strengths
  - market hard-filter warnings
  - root strength / interview-upskill / low-signal triage
  - resume targeting plan
  - memory updates
  - cover letter draft
  - recruiter message draft
- Tracks applications in a local CSV file.
- Optionally updates private local memory.
- Runs without external APIs.

## Demo: From Vibes To Evidence

```mermaid
quadrantChart
    title Ability Triage Map
    x-axis "Low evidence" --> "High evidence"
    y-axis "Hard to improve before interview" --> "Learnable before interview"
    quadrant-1 "Interview-upskill"
    quadrant-2 "Explore carefully"
    quadrant-3 "Do not claim"
    quadrant-4 "Root strength"
    "LLM workflow": [0.84, 0.72]
    "NLP extraction": [0.78, 0.65]
    "RPA basics": [0.42, 0.78]
    "German fluency": [0.18, 0.22]
    "Senior production ownership": [0.12, 0.18]
```

```text
Fit score: 95/100
Decision: Strong apply: tailor the resume and apply.

Market Hard Filters
- No hard market filter was detected by the local rules.
- Still verify location, language, and work authorization manually.

Ability Triage
Root Strengths
- python
- llm
- agent
- workflow
- nlp

Interview-Upskill Items
- rpa

Resume Targeting Plan
- Lead with the agentic AI workflow project.
- Quantify evaluation work where possible.
- Create a short interview-prep plan for learnable gaps.
- Do not publish generated resumes or application records.
```

## Quick Start

```bash
cd job-search-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Analyze a job:

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

Track an application:

```bash
job-agent track add \
  --company "Example Semiconductor" \
  --role "AI Automation Intern" \
  --status "tailoring" \
  --notes "Check language and onsite requirements before deep tailoring"

job-agent track list
```

## Privacy By Design 🔒

This repo is safe for public GitHub because the default profile is anonymized:

```text
profiles/sample_candidate.json
```

Do not commit private candidate data:

- real name
- phone number
- email
- date of birth
- student ID
- transcripts
- certificates
- visa or work-authorization details
- commute or address details
- real application records
- generated resumes

Ignored by default:

```text
data/private/
outputs/private/
outputs/
applications.csv
memory.local.json
*.local.json
*.docx
*.pdf
*.xlsx
*.xls
```

## Project Structure

```text
job-search-agent/
├── docs/
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
│   ├── profile.py
│   └── tracker.py
├── tests/
│   └── test_matcher.py
├── .gitignore
├── pyproject.toml
└── README.md
```

## Roadmap: From MVP To Job-Search OS

- Private memory dashboard.
- Better extraction of language, visa, location, commute, and start-date filters.
- Resume planner that refuses unsupported claims.
- Interview prep mode based on upskill items.
- Role-cluster analytics across applications.
- Optional LLM provider with strict factuality guards.
- Local web UI for reviewing the application pipeline.

## Why This Is Not Just Another Resume Tool

This README intentionally follows the 2025-2026 agent-project pattern: sharp thesis, local-first privacy, durable memory, visible workflow artifacts, and a clear anti-hype boundary.

Related signals:

- Agent memory is becoming a first-class research topic, with benchmarks focused on long-horizon and multi-session memory.
- Recent local-first memory projects emphasize private execution, auditability, and persistent context.
- Existing job-search tools often focus on ATS scores, resume tailoring, and auto-apply. This project focuses on precision, market filters, and truthful application strategy.

Useful references:

- [MemoryArena](https://digitaleconomy.stanford.edu/publication/memoryarena-benchmarking-agent-memory-in-interdependent-multi-session-agentic-tasks/) frames agent memory as multi-session learning, not just long context.
- [MemoryAgentBench](https://huggingface.co/papers/2507.05257) highlights retrieval, test-time learning, long-range understanding, and conflict resolution as memory-agent capabilities.
- [Memoria](https://github.com/matrixorigin/Memoria) positions agent memory around privacy, audit trails, snapshots, and rollback.
- [Sediment](https://github.com/rendro/sediment) is an example of the local-first memory README style: clear benchmark table, data location, and privacy promise.
- [resuml](https://github.com/phoinixi/resuml) shows the current resume-as-code direction: structured resume data, ATS checks, and AI-agent integration.
- [ApplyPilot](https://github.com/Pickle-Pixel/ApplyPilot) represents the opposite pole: autonomous job applications. This project deliberately chooses precision and review over auto-submit.

## Status

MVP.

Useful enough to show the idea.

Small enough to stay honest.

## Final Line

This is not a replacement for judgment.

It is a tool for making judgment harder to skip.

Do not use it to fabricate experience, hide hard constraints, or submit applications without review.
