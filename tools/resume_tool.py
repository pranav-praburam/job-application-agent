import os
from pathlib import Path
from crewai.tools import BaseTool


class ResumeTool(BaseTool):
    name: str = "Resume Reader"
    description: str = (
        "Read the candidate's base resume from disk. "
        "Returns the plain-text content of data/resume.txt."
    )
    resume_path: str = "data/resume.txt"

    def _run(self, _: str = "") -> str:
        path = Path(self.resume_path)
        if not path.exists():
            return (
                f"Resume not found at '{self.resume_path}'. "
                "Create data/resume.txt with your resume in plain text."
            )
        return path.read_text()
