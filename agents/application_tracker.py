from crewai import Agent, LLM
from tools.database_tool import DatabaseTool


def make_application_tracker(llm: LLM) -> Agent:
    return Agent(
        role="Application Tracker",
        goal=(
            "Read the saved jobs from the database and produce a plain-text pipeline summary. "
            "Never update or set any job status — that is done exclusively by the user."
        ),
        backstory=(
            "You are a read-only reporting assistant. You query the jobs database and summarise "
            "what was found: how many jobs, their companies, match scores, and recommended next steps. "
            "You do not modify any records."
        ),
        tools=[DatabaseTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
