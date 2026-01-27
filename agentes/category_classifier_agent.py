"""
Agente especializado em classificar problemas e sugerir código de categoria.
"""
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from config import Config
from rag import search_category_code
from prompts.prompt_category_classifier import category_classifier_instructions


def create_category_classifier_agent() -> Agent:
    """Cria o agente que encontra o código de categoria adequado."""
    return Agent(
        name="category_classifier_agent",
        model=LiteLlm(
            model=Config.BEDROCK_CLAUDE_MODEL,
            temperature=Config.TEMPERATURE,
            max_tokens=Config.MAX_TOKENS,
        ),
        instruction=category_classifier_instructions,
        description="Classifica o problema e encontra o código de categoria mais adequado",
        tools=[search_category_code],
    )
