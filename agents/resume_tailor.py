from crewai import Agent, LLM
from tools import ResumeTool


def make_resume_tailor(llm: LLM) -> Agent:
    return Agent(
        role="Resume Tailor",
        goal=(
            "Given a job description and the candidate's base resume, "
            "produce a tailored resume and a compelling cover letter."
        ),
        backstory=(
            "You are an expert career coach who rewrites resumes to highlight "
            "the most relevant experience for each specific role."
        ),
        tools=[ResumeTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
