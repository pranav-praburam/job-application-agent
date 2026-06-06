# Job Application Agent

A personal, AI-powered job application pipeline that automates the tedious parts of a job search — finding relevant postings, tailoring your resume, writing cover letters, and tracking every application — so you can focus on the conversations that matter.

## What it does

The pipeline runs a crew of specialized AI agents in sequence:

1. **Job Searcher** — scans the web for fresh postings that match your target roles and locations
2. **Resume Tailor** — reads your base resume and rewrites it (plus a cover letter) to match each job description
3. **Application Tracker** — logs every opportunity and status update to a local SQLite database, keeping your pipeline organized

## Tech stack

| Layer | Technology |
|---|---|
| Agent framework | [CrewAI](https://github.com/crewaiinc/crewai) 1.14.6 |
| Language model | OpenAI GPT-4o (swappable via `.env`) |
| Web search | SerperDev API (via `crewai-tools`) |
| Storage | SQLite (no external DB required) |
| Config | `python-dotenv` |
| Runtime | Python 3.12 |

## Project structure

```
agents/         CrewAI agent definitions (job searcher, resume tailor, tracker)
tools/          Custom CrewAI tools (database access, resume reader)
database/       SQLite schema and query helpers
data/           Your resume (resume.txt) and the generated applications.db
main.py         Entry point — builds and kicks off the crew
```

## Getting started

```bash
# 1. Activate the virtual environment
source .venv/bin/activate

# 2. Copy and fill in your API keys
cp .env.example .env

# 3. Add your resume as plain text
echo "Your resume content here" > data/resume.txt

# 4. Run the pipeline
python main.py
```

### Required API keys (in `.env`)

- `OPENAI_API_KEY` — powers the agents' reasoning
- `SERPER_API_KEY` — powers the job search web tool

### Optional configuration (in `.env`)

- `TARGET_ROLES` — comma-separated list of job titles to search for
- `TARGET_LOCATIONS` — comma-separated list of preferred locations
- `DATABASE_PATH` — path to the SQLite database file (default: `data/applications.db`)
