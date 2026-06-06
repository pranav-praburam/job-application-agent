import os
from crewai import LLM
from dotenv import load_dotenv

load_dotenv()


def get_llm() -> LLM:
    return LLM(
        model=os.getenv("MODEL_NAME", "anthropic/claude-sonnet-4-6"),
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )
