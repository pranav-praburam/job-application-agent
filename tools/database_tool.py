import json
import os
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import Field
from database import Database
from tools.match_scorer import score_match

_RESUME_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "resume.txt",
)


def _read_resume() -> str:
    p = Path(_RESUME_PATH)
    return p.read_text() if p.exists() else ""


class DatabaseTool(BaseTool):
    name: str = "Application Database"
    description: str = (
        "Save job postings to the SQLite database, or read existing application data. "
        "Input must be a JSON string with an 'action' key.\n"
        "Actions:\n"
        "  save_job         – save a job posting. Required fields: title, company, url. "
        "Optional: location, description. Status is always set to 'new' automatically "
        "and must NOT be changed by agents.\n"
        "  list_jobs        – list saved jobs (read-only). Optional 'limit' (default 50).\n"
    )
    db: Database = Field(default_factory=Database)

    model_config = {"arbitrary_types_allowed": True}

    def _run(self, query: str) -> str:
        try:
            params = json.loads(query)
        except json.JSONDecodeError:
            return "Error: input must be valid JSON."

        action = params.get("action")

        if action == "save_job":
            description = params.get("description", "")
            resume = _read_resume()
            match_score = score_match(description, resume) if description and resume else None

            job_id = self.db.upsert_job(
                title=params.get("title", "Unknown"),
                company=params.get("company", "Unknown"),
                url=params.get("url", ""),
                location=params.get("location"),
                description=description,
                source=params.get("source", "agent"),
                match_score=match_score,
            )
            score_str = f"{match_score}" if match_score is not None else "n/a (no resume found)"
            return json.dumps({"job_id": job_id, "match_score": score_str})

        if action == "list_jobs":
            rows = self.db.get_jobs(limit=params.get("limit", 50))
            return json.dumps(rows, default=str)

        return (
            f"Unknown action: '{action}'. "
            "Valid actions are: save_job, list_jobs. "
            "Note: job status can only be changed by the user via the dashboard — not by agents."
        )
