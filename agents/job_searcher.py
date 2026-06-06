from crewai import Agent, LLM
from crewai_tools import SerperDevTool
from tools.database_tool import DatabaseTool


def make_job_searcher(llm: LLM) -> Agent:
    return Agent(
        role="Job Searcher",
        goal=(
            "Find relevant job postings that match the candidate's target roles "
            "and locations, then save each one to the database."
        ),
        backstory=(
            "You are a meticulous recruiter's assistant who knows how to search "
            "the web for fresh job listings, surface only the most relevant ones, "
            "and record them with accurate URLs and descriptions."
        ),
        tools=[SerperDevTool(), DatabaseTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
