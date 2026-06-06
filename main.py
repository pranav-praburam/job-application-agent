import os
from pathlib import Path
from dotenv import load_dotenv
from crewai import Crew, Task

from agents import make_resume_tailor, make_application_tracker
from config import get_llm
from database import Database
from tools.serper_search import run_job_searches

load_dotenv()


def run_pipeline(role: str, location: str) -> str:
    db          = Database(path=os.getenv("DATABASE_PATH", "data/applications.db"))
    llm         = get_llm()
    resume_text = Path("data/resume.txt").read_text() if Path("data/resume.txt").exists() else ""
    api_key     = os.getenv("SERPER_API_KEY", "")

    # ── Phase 1: search (direct Python — reliable URL capture + logging) ──────
    print(f"\nSearching for '{role}' jobs …\n")
    new_jobs = run_job_searches(
        role=role,
        api_key=api_key,
        db=db,
        resume_text=resume_text,
        target_new=10,
        results_per_query=5,
    )

    if not new_jobs:
        print("\nNo new jobs found this run — all results were already in the database.")
        print("Try again later or widen the search by editing TARGET_ROLES in .env")
        return "No new jobs."

    # ── Phase 2: tailor + track (CrewAI) ─────────────────────────────────────
    resume_tailor = make_resume_tailor(llm)
    tracker       = make_application_tracker(llm)

    top = max(new_jobs, key=lambda j: j.get("match_score") or 0)
    new_titles = "\n".join(
        f"  - {j['title']} at {j['company']} (score: {j.get('match_score')}) — {j['url']}"
        for j in new_jobs
    )

    tailor_task = Task(
        description=(
            f"The job search just found {len(new_jobs)} new job(s):\n{new_titles}\n\n"
            f"The top match is: '{top['title']}' at {top['company']} (score: {top['match_score']}).\n"
            "Read the candidate's resume and write a tailored cover letter (3 paragraphs) "
            "for that top role, highlighting the most relevant experience."
        ),
        expected_output="A tailored cover letter (3 paragraphs) for the top-matching job.",
        agent=resume_tailor,
    )

    track_task = Task(
        description=(
            f"Summarise the pipeline run. {len(new_jobs)} new job(s) were found and saved:\n"
            f"{new_titles}\n\n"
            "Provide: total saved this run, top 3 by match score, "
            "and 2-3 concrete next steps for the user. "
            "Do NOT call any database tool or modify any data."
        ),
        expected_output=(
            "Plain-text summary: jobs found this run, top 3 with scores, next steps."
        ),
        agent=tracker,
        context=[tailor_task],
    )

    crew   = Crew(agents=[resume_tailor, tracker], tasks=[tailor_task, track_task], verbose=True)
    result = crew.kickoff()
    return str(result)


if __name__ == "__main__":
    role     = os.getenv("TARGET_ROLES",     "Data Engineer").split(",")[0].strip()
    location = os.getenv("TARGET_LOCATIONS", "Remote").split(",")[0].strip()

    print(f"Starting job application pipeline: {role} | {location}")
    output = run_pipeline(role, location)
    print("\n=== Pipeline Result ===")
    print(output)
